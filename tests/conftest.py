from __future__ import annotations

from pathlib import Path

import pytest

from douban_api.app import create_app
from douban_api.cache import TTLCache
from douban_api.config import Settings
from douban_api.errors import NotFoundError, UpstreamError
from douban_api.http import FetchResult
from douban_api.service import DoubanService

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeClient:
    """按 URL 返回本地 fixture，避免测试依赖外网。"""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.stats = {"requests": 0, "failures": 0, "retries_exhausted": 0, "bytes": 0}

    def get_html(self, url: str, *, timeout=None) -> FetchResult:
        self.calls.append(url)
        self.stats["requests"] += 1
        if "/subject/9999999" in url:
            raise NotFoundError(extra={"upstream": url})
        if "/boom" in url:
            raise UpstreamError("模拟上游故障")
        if "subject_search" in url:
            return FetchResult(read_fixture("search.html"), 200, 1.0, url)
        if "/latest" in url:
            return FetchResult(read_fixture("latest.html"), 200, 1.0, url)
        if "/tag/" in url:
            return FetchResult(read_fixture("tag.html"), 200, 1.0, url)
        if "/subject/" in url:
            return FetchResult(read_fixture("detail.html"), 200, 1.0, url)
        return FetchResult("<html></html>", 200, 1.0, url)

    def close(self) -> None:
        pass


@pytest.fixture
def settings() -> Settings:
    return Settings(
        rate_limit_rpm=0,
        ttl_latest=60,
        ttl_tag=60,
        ttl_detail=60,
        ttl_search=60,
        gzip_min_size=0,
        use_orjson=False,
    )


@pytest.fixture
def cache() -> TTLCache:
    return TTLCache(maxsize=64, default_ttl=60)


@pytest.fixture
def fake_client() -> FakeClient:
    return FakeClient()


@pytest.fixture
def service(settings: Settings, cache: TTLCache, fake_client: FakeClient) -> DoubanService:
    return DoubanService(settings, cache=cache, client=fake_client)  # type: ignore[arg-type]


@pytest.fixture
def app(settings: Settings, service: DoubanService):
    application = create_app(settings, service=service)
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()
