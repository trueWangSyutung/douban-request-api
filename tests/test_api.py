from __future__ import annotations

import gzip
import json

import pytest

from douban_api.app import create_app
from douban_api.config import Settings
from douban_api.errors import UpstreamError
from douban_api.service import DoubanService

from .conftest import FakeClient


def test_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "豆瓣图书查询 API" in response.get_data(as_text=True)


def test_landing_json(client):
    response = client.get("/?format=json")
    assert response.json["version"]
    assert "/api/v1/search" in response.json["endpoints"]


def test_latest_endpoint(client):
    response = client.get("/api/v1/books/latest")
    assert response.status_code == 200
    payload = response.json
    assert payload["code"] == 200
    assert payload["type"] == "全部"
    assert payload["page"] == 0
    assert len(payload["books"]) == 20
    assert payload["meta"]["cached"] is False


def test_second_request_hits_cache(client):
    first = client.get("/api/v1/books/tag?tag=小说")
    second = client.get("/api/v1/books/tag?tag=小说")
    assert first.status_code == second.status_code == 200
    assert first.json["meta"]["cached"] is False
    assert second.json["meta"]["cached"] is True
    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert second.json["books"] == first.json["books"]


def test_detail_endpoint(client):
    response = client.get("/api/v1/books/2567698")
    assert response.status_code == 200
    book = response.json["book"]
    assert book["id"] == "2567698"
    assert book["name"] == "三体"
    assert book["score"] == "8.9"


def test_search_endpoint(client):
    response = client.get("/api/v1/search?q=三体")
    assert response.status_code == 200
    payload = response.json
    assert payload["msg"] == "success"
    assert payload["q"] == "三体"
    assert len(payload["books"]) == 15
    assert payload.get("author") is None or isinstance(payload.get("author"), dict)


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("/api/v1/search", 10020),
        ("/api/v1/search?q=", 10021),
        ("/api/v1/books/tag", 10021),
        ("/api/v1/books/tag?tag=小说&page=0", 10022),
        ("/api/v1/books/tag?tag=小说&page=abc", 10020),
        ("/api/v1/books/abc", 10020),
        ("/api/v1/books/9999999", 10040),
        ("/getType?tag=", 10021),
        ("/getBookDetail", 10020),
    ],
)
def test_validation_errors(client, path, code):
    response = client.get(path)
    assert response.status_code in (400, 404)
    assert response.json["code"] == code
    assert response.json["msg"]


def test_legacy_paths_match_modern(client):
    legacy = client.get("/getType?tag=小说&page=1").json
    modern = client.get("/api/v1/books/tag?tag=小说&page=1").json
    assert legacy["books"] == modern["books"]


def test_gzip_compression(client):
    response = client.get("/api/v1/books/latest", headers={"Accept-Encoding": "gzip"})
    assert response.headers.get("Content-Encoding") == "gzip"
    assert "Accept-Encoding" in response.headers.get("Vary", "")
    decompressed = json.loads(gzip.decompress(response.data))
    assert decompressed["code"] == 200
    assert len(response.data) < 4096


def test_etag_returns_304(client):
    first = client.get("/api/v1/books/latest")
    etag = first.headers["ETag"]
    assert etag.startswith('W/"')
    second = client.get("/api/v1/books/latest", headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.data == b""


def test_cache_control_headers(client):
    response = client.get("/api/v1/books/latest")
    assert "public" in response.headers["Cache-Control"]
    assert "stale-while-revalidate" in response.headers["Cache-Control"]


def test_cors_headers(client):
    response = client.get("/healthz")
    assert response.headers["Access-Control-Allow-Origin"] == "*"


def test_health_and_metrics(client):
    health = client.get("/healthz")
    assert health.json["status"] == "ok"
    client.get("/api/v1/books/latest")
    client.get("/api/v1/books/latest")
    metrics = client.get("/metrics").json
    assert metrics["cache"]["hit"] >= 1
    assert metrics["upstream"]["requests"] >= 1
    assert metrics["settings"]["version"]


def test_openapi_and_docs(client):
    spec = client.get("/openapi.json").json
    assert spec["openapi"].startswith("3.1")
    assert "/api/v1/search" in spec["paths"]
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "swagger" in docs.get_data(as_text=True).lower()


def test_unknown_route_returns_json(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json["code"] == 10040


def test_upstream_failure_maps_to_502(settings, cache):
    class BoomClient(FakeClient):
        def get_html(self, url, *, timeout=None):
            raise UpstreamError("模拟上游超时")

    service = DoubanService(settings, cache=cache, client=BoomClient())  # type: ignore[arg-type]
    app = create_app(settings, service=service)
    app.config.update(TESTING=True)
    response = app.test_client().get("/api/v1/books/latest")
    assert response.status_code == 502
    assert response.json["code"] == 10030


def test_unexpected_error_returns_json_500(settings, cache):
    class BoomClient(FakeClient):
        def get_html(self, url, *, timeout=None):
            raise RuntimeError("boom")

    service = DoubanService(settings, cache=cache, client=BoomClient())  # type: ignore[arg-type]
    app = create_app(settings, service=service)
    app.config.update(TESTING=True)
    response = app.test_client().get("/api/v1/books/latest")
    assert response.status_code == 500
    assert response.json["code"] == 10070


def test_not_found_maps_to_404(settings, cache):
    service = DoubanService(settings, cache=cache, client=FakeClient())  # type: ignore[arg-type]
    app = create_app(settings, service=service)
    app.config.update(TESTING=True)
    response = app.test_client().get("/api/v1/books/9999999")
    assert response.status_code == 404
    assert response.json["code"] == 10040


def test_rate_limit(settings, cache):
    limited = settings.with_overrides(rate_limit_rpm=60, rate_limit_burst=1)
    service = DoubanService(limited, cache=cache, client=FakeClient())  # type: ignore[arg-type]
    app = create_app(limited, service=service)
    app.config.update(TESTING=True)
    client = app.test_client()
    assert client.get("/api/v1/books/latest").status_code == 200
    blocked = client.get("/api/v1/books/latest")
    assert blocked.status_code == 429
    assert blocked.json["code"] == 10050
    assert "Retry-After" in blocked.headers
    # 健康检查不受限流影响
    assert client.get("/healthz").status_code == 200


def test_public_cache_disabled(settings, cache):
    private = settings.with_overrides(public_cache=False)
    service = DoubanService(private, cache=cache, client=FakeClient())  # type: ignore[arg-type]
    app = create_app(private, service=service)
    app.config.update(TESTING=True)
    response = app.test_client().get("/api/v1/books/latest")
    assert response.headers["Cache-Control"] == "no-store"


def test_settings_from_env():
    settings = Settings.from_env(
        {
            "PORT": "9000",
            "RATE_LIMIT_RPM": "10",
            "TTL_TAG": "42",
            "REDIS_URL": "redis://localhost:6379/1",
            "PUBLIC_CACHE": "false",
            "HTTP_RETRIES": "9",
        }
    )
    assert settings.port == 9000
    assert settings.rate_limit_rpm == 10
    assert settings.ttl_tag == 42
    assert settings.cache_backend == "redis"
    assert settings.public_cache is False
    assert settings.retries == 5  # 上限保护
