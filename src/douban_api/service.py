"""业务编排层：校验 → 缓存 → 抓取 → 解析。

把"怎么取数据"和"怎么暴露 HTTP"分开，便于测试与复用（快照导出也用同一套）。
"""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from urllib.parse import quote

from .cache import MISSING, TTLCache, build_cache
from .config import Settings
from .errors import ApiError, EmptyParamError, NotFoundError, ParseError, ValidationError
from .http import UpstreamClient, get_client
from .parsers import parse_detail, parse_latest, parse_search_payload, parse_tag

logger = logging.getLogger(__name__)

_DATA_MARKER = re.compile(r"window\.__DATA__\s*=\s*")
_LEGACY_ASSET = Path(__file__).parent / "assets" / "legacy_decrypt.js"

_legacy_lock = threading.Lock()
_legacy_context = None
_legacy_error: str | None = None


def decrypt_legacy(payload: str) -> dict:
    """解码旧版加密的搜索负载（仅在豆瓣返回非 JSON 时触发）。

    旧实现每个请求 fork 一个 Node 进程（~100ms + 40MB），这里改用进程内 V8
    （quickjs，~1ms），并且只在真正需要时才加载 60KB 解密脚本。
    """
    global _legacy_context, _legacy_error
    with _legacy_lock:
        if _legacy_context is None and _legacy_error is None:
            try:
                import quickjs  # type: ignore

                context = quickjs.Context()
                context.set_memory_limit(256 * 1024 * 1024)
                context.eval(
                    "globalThis.console = {log: function(){}, error: function(){}, warn: function(){}};"
                )
                context.eval(_LEGACY_ASSET.read_text(encoding="utf-8"))
                context.eval("globalThis.__PAYLOAD__ = '';")
                _legacy_context = context
            except Exception as exc:
                _legacy_error = f"{exc.__class__.__name__}: {exc}"
                logger.warning("旧版解密脚本不可用：%s", _legacy_error)
        if _legacy_context is None:
            raise ParseError(
                "搜索数据为旧版加密格式，需安装可选依赖 quickjs（pip install 'douban-request-api[legacy]'）"
            )
        _legacy_context.set("__PAYLOAD__", payload)
        raw = _legacy_context.eval("JSON.stringify(decrypt(__PAYLOAD__))")
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise ParseError("旧版搜索数据解密失败") from exc


def extract_search_data(page: str) -> dict:
    """从搜索页取出 ``window.__DATA__``：新版是纯 JSON，旧版是加密字符串。"""
    marker = _DATA_MARKER.search(page)
    if not marker:
        raise ParseError("搜索页中未找到 window.__DATA__")
    rest = page[marker.end() :].lstrip()
    value: object
    try:
        value, _ = json.JSONDecoder().raw_decode(rest)
    except ValueError:
        quoted = re.match(r"""['"]([^'"]{16,})['"]""", rest)
        if not quoted:
            raise ParseError("搜索数据结构无法识别") from None
        value = decrypt_legacy(quoted.group(1))
    if isinstance(value, str):
        value = decrypt_legacy(value)
    if not isinstance(value, dict):
        raise ParseError("搜索数据结构异常")
    return value


class DoubanService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        cache: TTLCache | None = None,
        client: UpstreamClient | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.cache = cache if cache is not None else build_cache(self.settings)
        self.client = client or get_client(self.settings)

    # ------------------------------------------------------------------ 校验
    def _validate_text(self, value: str | None, name: str, *, max_len: int = 64) -> str:
        if value is None:
            raise ValidationError(f"缺少参数 {name}")
        value = value.strip()
        if not value:
            raise EmptyParamError(f"参数 {name} 不能为空")
        if len(value) > max_len:
            raise ValidationError(f"参数 {name} 过长（最多 {max_len} 字符）")
        if any(ord(ch) < 32 for ch in value):
            raise ValidationError(f"参数 {name} 含非法字符")
        return value

    def _validate_page(self, value: str | None, *, one_based: bool) -> int:
        if value in (None, ""):
            return 1 if one_based else 0
        try:
            page = int(str(value).strip())
        except (TypeError, ValueError):
            raise ValidationError("page 必须是整数") from None
        minimum = 1 if one_based else 0
        if page < minimum:
            raise ApiError(
                "页数不能小于等于 0" if one_based else "page 不能小于 0",
                code=10022,
                http_status=400,
            )
        if page > self.settings.max_page:
            raise ValidationError(f"page 超出上限（{self.settings.max_page}）")
        return page

    # ------------------------------------------------------------------ 抓取 + 缓存
    def _cached(self, key: str, ttl: int, loader) -> tuple[dict, bool]:
        """返回 (数据, 是否命中缓存)。"""
        hit = self.cache.peek(key) is not MISSING
        return self.cache.get_or_load(key, ttl, loader), hit

    def _fetch(self, url: str) -> str:
        result = self.client.get_html(url)
        logger.debug("GET %s -> %s in %.0fms", url, result.status, result.elapsed_ms)
        return result.text

    # ------------------------------------------------------------------ 对外能力
    def latest(self, subcat: str | None, page: str | None) -> tuple[dict, bool]:
        subcat = self._validate_text(subcat, "type", max_len=32) if subcat else "全部"
        page_number = self._validate_page(page, one_based=False)
        key = f"latest:{subcat}:{page_number}"

        def load() -> dict:
            url = f"{self.settings.upstream_base}/latest?subcat={quote(subcat)}&p={page_number}"
            books = parse_latest(self._fetch(url))
            return {"code": 200, "type": subcat, "page": page_number, "books": books}

        return self._cached(key, self.settings.ttl_latest, load)

    def tag(self, tag: str | None, page: str | None) -> tuple[dict, bool]:
        if tag is None:
            raise EmptyParamError("类型不能为空")
        tag = self._validate_text(tag, "tag", max_len=32)
        page_number = self._validate_page(page, one_based=True)
        key = f"tag:{tag}:{page_number}"

        def load() -> dict:
            start = (page_number - 1) * 20
            url = f"{self.settings.upstream_base}/tag/{quote(tag)}?start={start}&type=T"
            books = parse_tag(self._fetch(url))
            return {
                "code": 200,
                "tag": tag,
                "page": page_number,
                "start": start,
                "books": books,
            }

        return self._cached(key, self.settings.ttl_tag, load)

    def detail(self, subject_id: str | None) -> tuple[dict, bool]:
        if subject_id is None:
            raise ValidationError("缺少参数 id")
        subject_id = subject_id.strip()
        if not subject_id:
            raise EmptyParamError("参数 id 不能为空")
        if not re.fullmatch(r"\d{4,12}", subject_id):
            raise ValidationError("id 必须是 4-12 位数字的图书 ID")
        key = f"detail:{subject_id}"

        def load() -> dict:
            url = f"{self.settings.upstream_base}/subject/{subject_id}/"
            book = parse_detail(self._fetch(url))
            book["id"] = subject_id
            book["url"] = url
            return {"code": 200, "book": book}

        try:
            return self._cached(key, self.settings.ttl_detail, load)
        except NotFoundError:
            raise NotFoundError(f"图书 {subject_id} 不存在") from None

    def search(self, q: str | None) -> tuple[dict, bool]:
        q = self._validate_text(q, "q")
        key = f"search:{q}"

        def load() -> dict:
            url = f"{self.settings.search_base}/book/subject_search?search_text={quote(q)}"
            payload = extract_search_data(self._fetch(url))
            data = parse_search_payload(payload)
            data.update({"code": 200, "msg": "success", "q": data.get("q") or q})
            return data

        return self._cached(key, self.settings.ttl_search, load)

    # ------------------------------------------------------------------ 观测
    def stats(self) -> dict:
        cache_stats = self.cache.stats
        return {
            "cache": cache_stats,
            "upstream": self.client.stats,
        }


__all__ = ["DoubanService", "decrypt_legacy", "extract_search_data"]
