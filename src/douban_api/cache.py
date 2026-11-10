"""进程内 TTL + LRU 缓存，带单飞（single-flight）与过期数据兜底。

为什么要自己写：
* 依赖越少，Docker 镜像越小，冷启动越快；
* 需要"同一个 key 并发只打一次上游"（single-flight），避免缓存击穿；
* 需要在上游抖动时返回上一份过期数据（stale-while-error），保证可用性。

可选 ``REDIS_URL``：L1 内存 + L2 Redis，多 worker / 多副本共享缓存。
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)

_MISSING = object()
MISSING = _MISSING  # 公开别名，供上层判断缓存是否命中


@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float
    stale_until: float


class _Flight:
    __slots__ = ("error", "event", "value")

    def __init__(self) -> None:
        self.event = threading.Event()
        self.value: Any = _MISSING
        self.error: BaseException | None = None


class TTLCache:
    """线程安全的 TTL + LRU 缓存。``ttl=0`` 表示不缓存（永远回源）。"""

    def __init__(
        self,
        *,
        maxsize: int = 4096,
        default_ttl: int = 300,
        stale_multiplier: float = 6.0,
        clock: Callable[[], float] = time.monotonic,
        load_timeout: float = 30.0,
    ) -> None:
        self._data: OrderedDict[str, _Entry] = OrderedDict()
        self._inflight: dict[str, _Flight] = {}
        self._lock = threading.RLock()
        self._maxsize = max(1, int(maxsize))
        self._default_ttl = max(0, int(default_ttl))
        self._stale_multiplier = max(1.0, float(stale_multiplier))
        self._clock = clock
        self._load_timeout = load_timeout
        self._stats = {
            "hit": 0,
            "miss": 0,
            "stale": 0,
            "evict": 0,
            "load": 0,
            "coalesced": 0,
        }

    # ------------------------------------------------------------------ 基础读写
    def peek(self, key: str, *, allow_stale: bool = False) -> Any:
        """只读探测，不改变命中统计、不移除过期项。"""
        now = self._clock()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return _MISSING
            if entry.expires_at > now or (allow_stale and entry.stale_until > now):
                return entry.value
            return _MISSING

    def get(self, key: str, *, allow_stale: bool = False) -> Any:
        now = self._clock()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return _MISSING
            fresh = entry.expires_at > now
            if fresh or (allow_stale and entry.stale_until > now):
                self._data.move_to_end(key)
                self._stats["hit" if fresh else "stale"] += 1
                return entry.value
            self._data.pop(key, None)
            return _MISSING

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = self._default_ttl if ttl is None else max(0, int(ttl))
        if ttl == 0:
            return
        now = self._clock()
        with self._lock:
            self._data[key] = _Entry(value, now + ttl, now + ttl * self._stale_multiplier)
            self._data.move_to_end(key)
            while len(self._data) > self._maxsize:
                self._data.popitem(last=False)
                self._stats["evict"] += 1

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    # ------------------------------------------------------------------ 核心入口
    def get_or_load(self, key: str, ttl: int, loader: Callable[[], T]) -> T:
        """返回缓存值；过期则调用 ``loader`` 刷新；并发同 key 只执行一次 loader。"""
        ttl = self._default_ttl if ttl is None else max(0, int(ttl))
        if ttl == 0:
            self._stats["load"] += 1
            return loader()

        now = self._clock()
        with self._lock:
            entry = self._data.get(key)
            if entry is not None and entry.expires_at > now:
                self._data.move_to_end(key)
                self._stats["hit"] += 1
                return entry.value  # type: ignore[return-value]
            flight = self._inflight.get(key)
            leader = flight is None
            if leader:
                flight = _Flight()
                self._inflight[key] = flight
            else:
                self._stats["coalesced"] += 1

        if not leader:
            flight.event.wait(timeout=self._load_timeout)
            if flight.value is not _MISSING:
                return flight.value  # type: ignore[return-value]
            if flight.error is not None:
                raise flight.error
            raise TimeoutError(f"cache load timeout for key={key!r}")

        self._stats["miss"] += 1
        self._stats["load"] += 1
        try:
            value = loader()
        except BaseException as exc:
            stale = self.get(key, allow_stale=True)
            with self._lock:
                self._inflight.pop(key, None)
            flight.error = exc
            flight.event.set()
            if stale is not _MISSING:
                logger.warning("上游失败，返回过期缓存 key=%s err=%s", key, exc)
                return stale  # type: ignore[return-value]
            raise
        else:
            self.set(key, value, ttl)
            with self._lock:
                self._inflight.pop(key, None)
            flight.value = value
            flight.event.set()
            return value

    # ------------------------------------------------------------------ 观测
    @property
    def stats(self) -> dict[str, int]:
        with self._lock:
            data = dict(self._stats)
        requests = data["hit"] + data["miss"]
        data["size"] = len(self._data)
        data["hit_rate"] = round(data["hit"] / requests, 4) if requests else 0.0
        return data

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not _MISSING


class RedisCache:
    """L1（进程内）+ L2（Redis）两级缓存；Redis 不可用时自动降级为纯内存。"""

    def __init__(
        self,
        url: str,
        *,
        prefix: str = "douban:v2:",
        maxsize: int = 4096,
        default_ttl: int = 300,
        stale_multiplier: float = 6.0,
    ) -> None:
        import redis  # 延迟导入：未启用 Redis 时无需安装

        self._client = redis.Redis.from_url(
            url, socket_timeout=1.0, socket_connect_timeout=1.0, decode_responses=False
        )
        self._prefix = prefix
        self._l1 = TTLCache(
            maxsize=maxsize,
            default_ttl=default_ttl,
            stale_multiplier=stale_multiplier,
        )

    def _redis_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get_or_load(self, key: str, ttl: int, loader: Callable[[], T]) -> T:
        ttl = max(0, int(ttl))
        if ttl == 0:
            return loader()
        return self._l1.get_or_load(key, ttl, lambda: self._load_l2(key, ttl, loader))

    def _load_l2(self, key: str, ttl: int, loader: Callable[[], T]) -> T:
        redis_key = self._redis_key(key)
        try:
            raw = self._client.get(redis_key)
        except Exception as exc:
            logger.warning("Redis 读取失败，降级回源：%s", exc)
            raw = None
        if raw:
            try:
                return json.loads(raw)  # type: ignore[no-any-return]
            except (TypeError, ValueError):
                logger.warning("Redis 缓存内容损坏，忽略：%s", redis_key)
        value = loader()
        try:
            self._client.setex(redis_key, max(1, ttl), json.dumps(value, ensure_ascii=False))
        except Exception as exc:
            logger.warning("Redis 写入失败（忽略）：%s", exc)
        return value

    def clear(self) -> None:
        self._l1.clear()

    @property
    def stats(self) -> dict[str, int]:
        data = self._l1.stats
        data["backend"] = "redis"  # type: ignore[assignment]
        return data


def build_cache(settings: Any) -> TTLCache | RedisCache:
    """按配置构建缓存；Redis 连接失败时自动退化为内存缓存。"""
    if settings.redis_url:
        try:
            return RedisCache(
                settings.redis_url,
                prefix=settings.cache_prefix,
                maxsize=settings.cache_maxsize,
                default_ttl=settings.ttl_tag,
                stale_multiplier=settings.cache_stale_multiplier,
            )
        except Exception as exc:
            logger.warning("Redis 不可用，使用内存缓存：%s", exc)
    return TTLCache(
        maxsize=settings.cache_maxsize,
        default_ttl=settings.ttl_tag,
        stale_multiplier=settings.cache_stale_multiplier,
    )
