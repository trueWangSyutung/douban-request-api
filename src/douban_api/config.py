"""运行期配置：全部来自环境变量，方便 Docker / CI / 本地一致地调整。"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from .version import __version__

TRUE_VALUES = {"1", "true", "yes", "on", "y"}


def _env_str(env: Mapping[str, str], key: str, default: str) -> str:
    value = env.get(key)
    return default if value is None or value == "" else value


def _env_int(
    env: Mapping[str, str], key: str, default: int, *, lo: int | None = None, hi: int | None = None
) -> int:
    raw = env.get(key)
    try:
        value = int(raw) if raw not in (None, "") else default
    except ValueError:
        return default
    if lo is not None:
        value = max(lo, value)
    if hi is not None:
        value = min(hi, value)
    return value


def _env_float(
    env: Mapping[str, str],
    key: str,
    default: float,
    *,
    lo: float | None = None,
    hi: float | None = None,
) -> float:
    raw = env.get(key)
    try:
        value = float(raw) if raw not in (None, "") else default
    except ValueError:
        return default
    if lo is not None:
        value = max(lo, value)
    if hi is not None:
        value = min(hi, value)
    return value


def _env_bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in TRUE_VALUES


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class Settings:
    """一处配置，全局复用（不可变，便于测试时 ``replace``）。"""

    # --- HTTP 服务 ---
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    log_level: str = "info"

    # --- 上游抓取 ---
    upstream_base: str = "https://book.douban.com"
    search_base: str = "https://search.douban.com"
    user_agent: str = DEFAULT_UA
    connect_timeout: float = 3.5
    read_timeout: float = 7.0
    retries: int = 2
    pool_connections: int = 32
    pool_maxsize: int = 32
    verify_tls: bool = True

    # --- 缓存（秒）---
    ttl_latest: int = 300
    ttl_tag: int = 600
    ttl_detail: int = 1800
    ttl_search: int = 600
    cache_maxsize: int = 4096
    cache_stale_multiplier: float = 6.0
    redis_url: str = ""
    cache_prefix: str = "douban:v2:"

    # --- 响应 ---
    gzip_min_size: int = 512
    gzip_level: int = 6
    cors_origins: str = "*"
    public_cache: bool = True
    use_orjson: bool = True

    # --- 保护 ---
    rate_limit_rpm: int = 120
    rate_limit_burst: int = 0
    trust_proxy: bool = False
    max_page: int = 50

    # --- 其它 ---
    warmup: bool = False
    snapshot_details: int = 30
    extra: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        return cls(
            host=_env_str(env, "HOST", "0.0.0.0"),
            port=_env_int(env, "PORT", 5000, lo=1, hi=65535),
            debug=_env_bool(env, "DEBUG", False),
            log_level=_env_str(env, "LOG_LEVEL", "info"),
            upstream_base=_env_str(env, "UPSTREAM_BASE", "https://book.douban.com").rstrip("/"),
            search_base=_env_str(env, "SEARCH_BASE", "https://search.douban.com").rstrip("/"),
            user_agent=_env_str(env, "USER_AGENT", DEFAULT_UA),
            connect_timeout=_env_float(env, "CONNECT_TIMEOUT", 3.5, lo=0.5, hi=30),
            read_timeout=_env_float(env, "READ_TIMEOUT", 7.0, lo=0.5, hi=60),
            retries=_env_int(env, "HTTP_RETRIES", 2, lo=0, hi=5),
            pool_connections=_env_int(env, "POOL_CONNECTIONS", 32, lo=1, hi=256),
            pool_maxsize=_env_int(env, "POOL_MAXSIZE", 32, lo=1, hi=256),
            verify_tls=_env_bool(env, "VERIFY_TLS", True),
            ttl_latest=_env_int(env, "TTL_LATEST", 300, lo=0),
            ttl_tag=_env_int(env, "TTL_TAG", 600, lo=0),
            ttl_detail=_env_int(env, "TTL_DETAIL", 1800, lo=0),
            ttl_search=_env_int(env, "TTL_SEARCH", 600, lo=0),
            cache_maxsize=_env_int(env, "CACHE_MAXSIZE", 4096, lo=1),
            cache_stale_multiplier=_env_float(env, "CACHE_STALE_MULTIPLIER", 6.0, lo=0, hi=100),
            redis_url=_env_str(env, "REDIS_URL", ""),
            cache_prefix=_env_str(env, "CACHE_PREFIX", "douban:v2:"),
            gzip_min_size=_env_int(env, "GZIP_MIN_SIZE", 512, lo=0),
            gzip_level=_env_int(env, "GZIP_LEVEL", 6, lo=1, hi=9),
            cors_origins=_env_str(env, "CORS_ORIGINS", "*"),
            public_cache=_env_bool(env, "PUBLIC_CACHE", True),
            use_orjson=_env_bool(env, "USE_ORJSON", True),
            rate_limit_rpm=_env_int(env, "RATE_LIMIT_RPM", 120, lo=0),
            rate_limit_burst=_env_int(env, "RATE_LIMIT_BURST", 0, lo=0),
            trust_proxy=_env_bool(env, "TRUST_PROXY", False),
            max_page=_env_int(env, "MAX_PAGE", 50, lo=1, hi=500),
            warmup=_env_bool(env, "WARMUP", False),
            snapshot_details=_env_int(env, "SNAPSHOT_DETAILS", 30, lo=0),
        )

    def with_overrides(self, **kwargs) -> Settings:
        return replace(self, **kwargs)

    @property
    def upstream_timeout(self) -> tuple[float, float]:
        return (self.connect_timeout, self.read_timeout)

    @property
    def cache_backend(self) -> str:
        return "redis" if self.redis_url else "memory"

    def describe(self) -> dict[str, object]:
        return {
            "version": __version__,
            "cache_backend": self.cache_backend,
            "ttl": {
                "latest": self.ttl_latest,
                "tag": self.ttl_tag,
                "detail": self.ttl_detail,
                "search": self.ttl_search,
            },
            "rate_limit_rpm": self.rate_limit_rpm,
            "gzip_min_size": self.gzip_min_size,
            "upstream_timeout": list(self.upstream_timeout),
        }
