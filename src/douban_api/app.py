"""Flask 应用工厂：路由、压缩、ETag/304、CORS、限流、错误处理。

性能相关的 HTTP 层细节：
* gzip 压缩（JSON 体积通常从 ~25KB 降到 ~3KB）；
* 弱 ETag + ``If-None-Match`` → 304，客户端可以零流量刷新；
* ``Cache-Control: public, max-age=..., stale-while-revalidate=...``；
* ``X-Cache: HIT|MISS`` 与 ``X-Response-Time`` 便于观测。
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import time
import uuid
from typing import Any

from flask import Flask, Response, g, jsonify, request
from werkzeug.exceptions import HTTPException

from .config import Settings
from .errors import ApiError, RateLimitedError
from .openapi import build_spec
from .rate_limit import TokenBucketLimiter
from .service import DoubanService
from .version import __version__

logger = logging.getLogger(__name__)

JSON_MIME = "application/json; charset=utf-8"

LANDING_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>豆瓣图书查询 API v{version}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.65 -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
         max-width: 780px; margin: 6vh auto; padding: 0 20px; }}
  code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }}
  pre {{ background: rgba(127,127,127,.12); padding: 14px 16px; border-radius: 10px; overflow-x: auto; }}
  .tag {{ display: inline-block; font-size: 12px; padding: 2px 8px; border-radius: 999px;
         background: rgba(0,150,90,.14); color: #0a7d4f; margin-left: 8px; vertical-align: middle; }}
  a {{ color: #0a7d4f; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td, th {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid rgba(127,127,127,.2); }}
</style>
</head>
<body>
<h1>豆瓣图书查询 API <span class="tag">v{version}</span></h1>
<p>服务运行中，缓存后端 <code>{backend}</code>。接口文档：<a href="{docs}">{docs}</a></p>
<table>
  <tr><th>接口</th><th>说明</th></tr>
  <tr><td><code>GET /api/v1/books/latest?type=全部&amp;page=0</code></td><td>最新图书</td></tr>
  <tr><td><code>GET /api/v1/books/tag?tag=小说&amp;page=1</code></td><td>标签图书</td></tr>
  <tr><td><code>GET /api/v1/books/2567698</code></td><td>图书详情</td></tr>
  <tr><td><code>GET /api/v1/search?q=三体</code></td><td>关键词搜索</td></tr>
  <tr><td><code>GET /healthz</code> / <code>GET /metrics</code></td><td>健康检查 / 运行指标</td></tr>
</table>
<p>旧版路径 <code>/getNewBook</code>、<code>/getType</code>、<code>/getBookDetail</code>、
<code>/search</code> 继续可用。</p>
<pre>curl -s "{origin}/api/v1/search?q=三体" | head -c 400</pre>
<p style="opacity:.65;font-size:13px">数据来自豆瓣，仅供学习研究，请勿高频遍历。</p>
</body>
</html>
"""


def _configure_json(app: Flask, settings: Settings) -> None:
    app.json.ensure_ascii = False
    if not settings.use_orjson:
        return
    try:
        import orjson

        class OrjsonProvider(app.json.__class__):  # type: ignore[misc, valid-type]
            ensure_ascii = False

            def dumps(self, obj: Any, **kwargs: Any) -> str:
                return orjson.dumps(obj, option=orjson.OPT_NON_STR_KEYS).decode("utf-8")

            def loads(self, s: str | bytes, **kwargs: Any) -> Any:
                return orjson.loads(s)

        app.json = OrjsonProvider(app)
        logger.debug("使用 orjson 序列化")
    except ImportError:
        pass


def _etag_matches(header: str | None, etag: str) -> bool:
    """RFC 7232 弱比较：``If-None-Match`` 里的 W/ 前缀不参与比较。

    Werkzeug 的 ``request.if_none_match`` 会丢弃弱标签（``W/"..."``），
    这里自己解析，避免 304 永远不命中。
    """
    if not header:
        return False
    header = header.strip()
    if header == "*":
        return True
    target = etag[2:] if etag.startswith("W/") else etag
    for candidate in header.split(","):
        candidate = candidate.strip()
        if candidate.startswith("W/"):
            candidate = candidate[2:]
        if candidate == target:
            return True
    return False


def _client_key(settings: Settings) -> str:
    if settings.trust_proxy:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _json(
    payload: dict, *, status: int = 200, ttl: int | None = None, cached: bool | None = None
) -> Response:
    response = jsonify(payload)
    response.status_code = status
    g.cache_ttl = ttl
    if cached is not None:
        g.cache_status = "HIT" if cached else "MISS"
    # ETag 只反映业务数据：meta 里的 elapsed_ms / cached 每次请求都不同，
    # 若参与计算会导致 304 永远失效。
    stable = {key: value for key, value in payload.items() if key != "meta"}
    g.etag_source = json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str).encode()
    return response


def _with_meta(payload: dict, *, cached: bool, elapsed_ms: float, ttl: int) -> dict:
    meta = payload.setdefault("meta", {})
    meta.update(
        {
            "cached": cached,
            "elapsed_ms": round(elapsed_ms, 2),
            "ttl": ttl,
            "version": __version__,
        }
    )
    return payload


def create_app(settings: Settings | None = None, *, service: DoubanService | None = None) -> Flask:
    settings = settings or Settings.from_env()
    app = Flask(__name__)
    app.config.update(
        SETTINGS=settings,
        JSON_SORT_KEYS=False,
        MAX_CONTENT_LENGTH=64 * 1024,
        DEBUG=settings.debug,
    )
    if not app.debug:
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    _configure_json(app, settings)

    svc = service or DoubanService(settings)
    limiter = TokenBucketLimiter(settings.rate_limit_rpm, burst=settings.rate_limit_burst or None)
    app.extensions["douban_service"] = svc
    app.extensions["douban_limiter"] = limiter
    app.extensions["douban_settings"] = settings

    spec = build_spec()

    # ------------------------------------------------------------------ 路由
    def latest_view():
        started = time.perf_counter()
        data, cached = svc.latest(request.args.get("type"), request.args.get("page"))
        ttl = settings.ttl_latest
        return _json(
            _with_meta(
                data, cached=cached, elapsed_ms=(time.perf_counter() - started) * 1000, ttl=ttl
            ),
            ttl=ttl,
            cached=cached,
        )

    def tag_view():
        started = time.perf_counter()
        data, cached = svc.tag(request.args.get("tag"), request.args.get("page"))
        ttl = settings.ttl_tag
        return _json(
            _with_meta(
                data, cached=cached, elapsed_ms=(time.perf_counter() - started) * 1000, ttl=ttl
            ),
            ttl=ttl,
            cached=cached,
        )

    def detail_view(subject_id: str | None):
        started = time.perf_counter()
        data, cached = svc.detail(subject_id)
        ttl = settings.ttl_detail
        return _json(
            _with_meta(
                data, cached=cached, elapsed_ms=(time.perf_counter() - started) * 1000, ttl=ttl
            ),
            ttl=ttl,
            cached=cached,
        )

    def search_view():
        started = time.perf_counter()
        data, cached = svc.search(request.args.get("q"))
        ttl = settings.ttl_search
        return _json(
            _with_meta(
                data, cached=cached, elapsed_ms=(time.perf_counter() - started) * 1000, ttl=ttl
            ),
            ttl=ttl,
            cached=cached,
        )

    def detail_query_view():
        # 旧版 /getBookDetail?id=xxx：参数来自 query 而不是路径
        return detail_view(request.args.get("id"))

    def health_view():
        return _json(
            {
                "status": "ok",
                "version": __version__,
                "uptime_s": round(time.time() - START_TIME, 1),
                "cache_backend": settings.cache_backend,
            },
            ttl=0,
        )

    def metrics_view():
        stats = svc.stats()
        stats["version"] = __version__
        stats["settings"] = settings.describe()
        return _json(stats, ttl=0)

    def openapi_view():
        return _json(spec, ttl=3600)

    def docs_view():
        return Response(
            _SWAGGER_HTML.replace("__SPEC_URL__", "/openapi.json"), mimetype="text/html"
        )

    def landing_view():
        if request.args.get("format") == "json" or (
            "application/json" in request.headers.get("Accept", "")
            and "text/html" not in request.headers.get("Accept", "")
        ):
            return _json(
                {
                    "name": "豆瓣图书查询 API",
                    "version": __version__,
                    "docs": "/docs",
                    "openapi": "/openapi.json",
                    "endpoints": [
                        "/api/v1/books/latest",
                        "/api/v1/books/tag",
                        "/api/v1/books/{id}",
                        "/api/v1/search",
                        "/healthz",
                        "/metrics",
                    ],
                },
                ttl=0,
            )
        return Response(
            LANDING_HTML.format(
                version=__version__,
                backend=settings.cache_backend,
                docs="/docs",
                origin=request.url_root.rstrip("/"),
            ),
            mimetype="text/html",
        )

    modern = {
        "/books/latest": ("books_latest", latest_view),
        "/books/tag": ("books_tag", tag_view),
        "/books/<subject_id>": ("books_detail", detail_view),
        "/search": ("books_search", search_view),
    }
    for rule, (name, view) in modern.items():
        app.add_url_rule(f"/api/v1{rule}", endpoint=f"v1_{name}", view_func=view)

    legacy = {
        "/getNewBook": ("legacy_latest", latest_view),
        "/getType": ("legacy_tag", tag_view),
        "/getBookDetail": ("legacy_detail", detail_query_view),
        "/search": ("legacy_search", search_view),
    }
    for rule, (name, view) in legacy.items():
        app.add_url_rule(rule, endpoint=name, view_func=view)

    app.add_url_rule("/", endpoint="landing", view_func=landing_view)
    app.add_url_rule("/healthz", endpoint="healthz", view_func=health_view)
    app.add_url_rule("/metrics", endpoint="metrics", view_func=metrics_view)
    app.add_url_rule("/openapi.json", endpoint="openapi", view_func=openapi_view)
    app.add_url_rule("/docs", endpoint="docs", view_func=docs_view)
    app.add_url_rule("/favicon.ico", endpoint="favicon", view_func=lambda: Response(status=204))

    # ------------------------------------------------------------------ 钩子
    @app.before_request
    def _before() -> Response | None:
        g.start = time.perf_counter()
        g.request_id = uuid.uuid4().hex[:12]
        g.cache_ttl = None
        path = request.path
        if not limiter.enabled or path.startswith(("/healthz", "/metrics", "/docs", "/openapi")):
            return None
        allowed, remaining, retry_after = limiter.consume(_client_key(settings))
        if allowed:
            g.rate_remaining = remaining
            return None
        error = RateLimitedError()
        response = jsonify(error.to_dict())
        response.status_code = error.http_status
        response.headers["Retry-After"] = str(max(1, int(retry_after + 0.5)))
        response.headers["X-RateLimit-Remaining"] = "0"
        return response

    @app.after_request
    def _after(response: Response) -> Response:
        response.headers["X-Request-Id"] = getattr(g, "request_id", "")
        response.headers["X-Response-Time"] = (
            f"{(time.perf_counter() - getattr(g, 'start', time.perf_counter())) * 1000:.1f}ms"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers.setdefault("Access-Control-Allow-Origin", settings.cors_origins)
        response.headers["Access-Control-Expose-Headers"] = (
            "X-Cache, X-Response-Time, X-Request-Id, X-RateLimit-Remaining, ETag"
        )
        if remaining := getattr(g, "rate_remaining", None):
            response.headers["X-RateLimit-Remaining"] = str(remaining)

        ttl = getattr(g, "cache_ttl", None)
        is_json = response.mimetype == "application/json"
        if is_json and ttl is not None:
            response.headers["X-Cache"] = g.get("cache_status", "HIT" if ttl else "BYPASS")
            if settings.public_cache and ttl:
                response.headers["Cache-Control"] = (
                    f"public, max-age={max(1, ttl // 2)}, stale-while-revalidate={ttl}"
                )
            else:
                response.headers["Cache-Control"] = "no-store"
        elif response.status_code >= 400:
            response.headers["Cache-Control"] = "no-store"

        if response.status_code == 200 and is_json and not response.direct_passthrough:
            body = response.get_data()
            etag = (
                'W/"'
                + hashlib.blake2b(getattr(g, "etag_source", body), digest_size=8).hexdigest()
                + '"'
            )
            response.headers["ETag"] = etag
            if request.method in ("GET", "HEAD") and _etag_matches(
                request.headers.get("If-None-Match"), etag
            ):
                response.status_code = 304
                response.set_data(b"")
                response.headers.pop("Content-Encoding", None)
                response.headers["Cache-Control"] = f"public, max-age={max(1, (ttl or 60) // 2)}"
                return response

            accepts_gzip = "gzip" in request.headers.get("Accept-Encoding", "").lower()
            if accepts_gzip and len(body) >= settings.gzip_min_size:
                compressed = gzip.compress(body, compresslevel=settings.gzip_level)
                if len(compressed) < len(body) * 0.95:
                    response.set_data(compressed)
                    response.headers["Content-Encoding"] = "gzip"
                    vary = response.headers.get("Vary", "")
                    if "Accept-Encoding" not in vary:
                        response.headers["Vary"] = f"{vary}, Accept-Encoding".strip(", ")
        return response

    @app.errorhandler(ApiError)
    def _handle_api_error(error: ApiError):
        response = jsonify(error.to_dict())
        response.status_code = error.http_status
        return response

    @app.errorhandler(HTTPException)
    def _handle_http_error(error: HTTPException):
        code = {400: 10020, 404: 10040, 405: 10020, 429: 10050}.get(error.code or 500, 10070)
        response = jsonify({"code": code, "msg": error.description})
        response.status_code = error.code or 500
        return response

    @app.errorhandler(Exception)
    def _handle_unexpected(error: Exception):
        logger.exception("未处理异常：%s", error)
        response = jsonify({"code": 10070, "msg": "服务内部错误"})
        response.status_code = 500
        return response

    return app


START_TIME = time.time()

_SWAGGER_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>豆瓣图书查询 API - 接口文档</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
<style>body{margin:0;background:#fafafa}</style>
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js" crossorigin></script>
<script>
window.addEventListener('load', function () {
  window.ui = SwaggerUIBundle({url: '__SPEC_URL__', dom_id: '#swagger-ui', deepLinking: true});
});
</script>
</body>
</html>
"""
