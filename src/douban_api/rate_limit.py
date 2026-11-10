"""极简令牌桶限流：保护自己，也保护豆瓣（避免被风控）。"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class TokenBucketLimiter:
    def __init__(
        self, rpm: int, *, burst: int | None = None, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.rpm = max(0, int(rpm))
        self.rate = self.rpm / 60.0
        self.burst = float(burst if burst is not None else max(10, min(200, self.rpm // 2 or 10)))
        self._clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.rpm > 0

    def consume(self, key: str) -> tuple[bool, int, float]:
        """返回 (是否放行, 剩余令牌, 需要等待的秒数)。"""
        if not self.enabled:
            return True, 0, 0.0
        now = self._clock()
        with self._lock:
            tokens, updated = self._buckets.get(key, (self.burst, now))
            tokens = min(self.burst, tokens + (now - updated) * self.rate)
            if tokens >= 1.0:
                self._buckets[key] = (tokens - 1.0, now)
                allowed, remaining = True, int(tokens - 1.0)
            else:
                self._buckets[key] = (tokens, now)
                allowed, remaining = False, 0
            if len(self._buckets) > 20000:
                self._prune(now)
        retry_after = 0.0 if allowed else round((1.0 - tokens) / self.rate, 2) if self.rate else 1.0
        return allowed, remaining, retry_after

    def _prune(self, now: float) -> None:
        stale = [
            k
            for k, (tokens, ts) in self._buckets.items()
            if tokens >= self.burst - 0.001 and now - ts > 60
        ]
        for key in stale[:10000]:
            self._buckets.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
