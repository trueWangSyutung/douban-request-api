from __future__ import annotations

import pytest

from douban_api.errors import ApiError, EmptyParamError, ValidationError
from douban_api.service import DoubanService, extract_search_data

from .conftest import read_fixture


def test_latest_builds_url_and_caches(service: DoubanService, fake_client):
    data, cached = service.latest("全部", None)
    assert cached is False
    assert data["code"] == 200
    assert "subcat=%E5%85%A8%E9%83%A8" in fake_client.calls[0]
    assert fake_client.calls[0].endswith("&p=0")

    again, cached_again = service.latest("全部", None)
    assert cached_again is True
    assert again["books"] == data["books"]
    assert len(fake_client.calls) == 1


def test_tag_pagination_offset(service: DoubanService, fake_client):
    service.tag("小说", "3")
    assert "start=40" in fake_client.calls[0]
    assert "%E5%B0%8F%E8%AF%B4" in fake_client.calls[0]


def test_detail_requires_numeric_id(service: DoubanService):
    with pytest.raises(ValidationError):
        service.detail("not-a-number")
    with pytest.raises(ValidationError):
        service.detail(None)
    with pytest.raises(EmptyParamError):
        service.detail("   ")


@pytest.mark.parametrize("page", ["0", "-1", "abc", "999"])
def test_invalid_pages_rejected(service: DoubanService, page: str):
    with pytest.raises(ApiError):
        service.tag("小说", page)


def test_search_returns_structured_result(service: DoubanService):
    data, cached = service.search("三体")
    assert cached is False
    assert data["q"] == "三体"
    assert data["books"][0]["name"].startswith("三体")


def test_search_requires_query(service: DoubanService):
    with pytest.raises(ValidationError):
        service.search(None)
    with pytest.raises(EmptyParamError):
        service.search("  ")


def test_extract_search_data_handles_whitespace_and_semicolons():
    page = 'window.__DATA__ = {"items": [], "text": "a;b"};</script>'
    assert extract_search_data(page)["text"] == "a;b"


def test_search_fixture_inline_marker():
    data = extract_search_data(read_fixture("search.html"))
    assert data["count"] == 15
