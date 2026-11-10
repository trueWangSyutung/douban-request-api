from __future__ import annotations

import threading
import time

import pytest

from douban_api.cache import MISSING, TTLCache


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def cache(clock: Clock) -> TTLCache:
    return TTLCache(maxsize=3, default_ttl=60, stale_multiplier=2.0, clock=clock)


def test_set_get_and_expire(cache: TTLCache, clock: Clock):
    cache.set("a", {"v": 1}, 10)
    assert cache.get("a") == {"v": 1}
    clock.advance(9)
    assert cache.get("a") == {"v": 1}
    clock.advance(2)
    assert cache.get("a") is MISSING


def test_stale_served_when_loader_fails(cache: TTLCache, clock: Clock):
    cache.set("a", "old", 10)
    clock.advance(11)  # 过期但仍在 stale 窗口内（10 * 2）

    def boom():
        raise RuntimeError("upstream down")

    assert cache.get_or_load("a", 10, boom) == "old"
    assert cache.stats["stale"] == 1


def test_error_propagates_without_stale(cache: TTLCache):
    def boom():
        raise RuntimeError("upstream down")

    with pytest.raises(RuntimeError):
        cache.get_or_load("missing", 10, boom)


def test_lru_eviction(cache: TTLCache):
    for key in ("a", "b", "c"):
        cache.set(key, key, 60)
    cache.get("a")  # a 变成最近使用
    cache.set("d", "d", 60)
    assert cache.get("b") is MISSING
    assert cache.get("a") == "a"
    assert len(cache) == 3


def test_ttl_zero_bypasses_cache(cache: TTLCache):
    calls = []
    assert cache.get_or_load("k", 0, lambda: calls.append(1) or "v") == "v"
    assert cache.get_or_load("k", 0, lambda: calls.append(1) or "v") == "v"
    assert len(calls) == 2
    assert cache.peek("k") is MISSING


def test_peek_does_not_count_hits(cache: TTLCache):
    cache.set("a", 1, 60)
    assert cache.peek("a") == 1
    assert cache.stats["hit"] == 0
    assert cache.peek("nope") is MISSING


def test_single_flight(clock: Clock):
    cache = TTLCache(maxsize=8, default_ttl=60, clock=clock)
    calls = {"n": 0}
    started = threading.Event()

    def loader():
        calls["n"] += 1
        started.set()
        time.sleep(0.15)
        return "value"

    results: list[str] = []
    errors: list[BaseException] = []

    def worker():
        try:
            results.append(cache.get_or_load("same", 60, loader))
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    started.wait(timeout=2)
    for thread in threads:
        thread.join(timeout=5)

    assert not errors
    assert calls["n"] == 1, "并发同 key 只应回源一次"
    assert results == ["value"] * 8
    assert cache.stats["coalesced"] >= 7


def test_clear_and_contains(cache: TTLCache):
    cache.set("a", 1, 60)
    assert "a" in cache
    cache.clear()
    assert "a" not in cache
    assert len(cache) == 0
