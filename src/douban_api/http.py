"""上游 HTTP 客户端：连接池 + keep-alive + 超时 + 有限重试 + gzip。

旧实现每个请求都调用 ``requests.get``，等价于每次重新三次握手 + TLS 协商；
这里改为进程级 ``Session``，复用 TCP 连接，并只做幂等的 GET 重试。
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Settings
from .errors import NotFoundError, UpstreamError

logger = logging.getLogger(__name__)

_HTML_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"


@dataclass(slots=True)
class FetchResult:
    text: str
    status: int
    elapsed_ms: float
    url: str


def _build_session(settings: Settings) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=settings.retries,
        connect=settings.retries,
        read=settings.retries,
        status=settings.retries,
        backoff_factor=0.25,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        pool_connections=settings.pool_connections,
        pool_maxsize=settings.pool_maxsize,
        max_retries=retry,
        pool_block=False,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": settings.user_agent,
            "Accept": _HTML_ACCEPT,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Referer": settings.upstream_base + "/",
        }
    )
    return session


class UpstreamClient:
    """线程安全的上游抓取客户端（Session 本身线程安全，仅懒初始化需要加锁）。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._session: requests.Session | None = None
        self._lock = threading.Lock()
        self._stats = {"requests": 0, "failures": 0, "retries_exhausted": 0, "bytes": 0}

    # ------------------------------------------------------------------ 内部
    @property
    def session(self) -> requests.Session:
        if self._session is None:
            with self._lock:
                if self._session is None:
                    self._session = _build_session(self._settings)
        return self._session

    # ------------------------------------------------------------------ 对外
    def get_html(self, url: str, *, timeout: tuple[float, float] | None = None) -> FetchResult:
        started = time.perf_counter()
        try:
            response = self.session.get(
                url,
                timeout=timeout or self._settings.upstream_timeout,
                allow_redirects=True,
            )
        except requests.Timeout as exc:
            self._stats["failures"] += 1
            raise UpstreamError(f"上游请求超时：{url}", extra={"upstream": url}) from exc
        except requests.RequestException as exc:
            self._stats["failures"] += 1
            raise UpstreamError(
                f"上游请求失败：{exc.__class__.__name__}", extra={"upstream": url}
            ) from exc

        elapsed_ms = (time.perf_counter() - started) * 1000
        self._stats["requests"] += 1
        self._stats["bytes"] += len(response.content or b"")

        if response.status_code == 404:
            raise NotFoundError(extra={"upstream": url})
        if response.status_code >= 500:
            self._stats["retries_exhausted"] += 1
            raise UpstreamError(
                f"上游返回 {response.status_code}", extra={"upstream_status": response.status_code}
            )
        if response.status_code >= 400:
            raise UpstreamError(
                f"上游拒绝请求（{response.status_code}），可能触发风控，请降低频率",
                extra={"upstream_status": response.status_code},
            )

        # 豆瓣页面为 UTF-8；显式指定避免 requests 猜测错误导致中文乱码
        response.encoding = "utf-8"
        return FetchResult(
            text=response.text,
            status=response.status_code,
            elapsed_ms=round(elapsed_ms, 2),
            url=str(response.url),
        )

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)


_client_lock = threading.Lock()
_default_client: UpstreamClient | None = None


def get_client(settings: Settings | None = None) -> UpstreamClient:
    """进程级单例，保证连接池被复用。"""
    global _default_client
    if _default_client is None:
        with _client_lock:
            if _default_client is None:
                _default_client = UpstreamClient(settings)
    return _default_client


def reset_client() -> None:
    global _default_client
    with _client_lock:
        if _default_client is not None:
            _default_client.close()
        _default_client = None
