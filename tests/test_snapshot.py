from __future__ import annotations

import json
from pathlib import Path

from douban_api.snapshot import build_snapshot

from .conftest import FakeClient


def test_snapshot_writes_static_api(tmp_path: Path, service, fake_client: FakeClient):
    report = build_snapshot(service, tmp_path, tags=["小说", "科幻"], details=2)
    api = tmp_path / "api" / "v1"

    assert report.errors == []
    assert report.files >= 7
    assert report.books >= 30
    assert report.details == 2

    latest = json.loads((api / "books" / "latest.json").read_text(encoding="utf-8"))
    assert latest["code"] == 200
    assert latest["meta"]["source"] == "snapshot"
    assert len(latest["books"]) == 20

    tag = json.loads((api / "books" / "tag" / "小说.json").read_text(encoding="utf-8"))
    assert tag["tag"] == "小说"
    assert len(tag["books"]) == 20

    index = json.loads((api / "search" / "index.json").read_text(encoding="utf-8"))
    assert index["count"] == report.books
    assert all(book["id"] for book in index["books"])

    manifest = json.loads((api / "index.json").read_text(encoding="utf-8"))
    assert manifest["tags"] == ["小说", "科幻"]
    assert manifest["version"]

    health = json.loads((api / "health.json").read_text(encoding="utf-8"))
    assert health["mode"] == "snapshot"

    details = list((api / "books").glob("*.json"))
    assert len([p for p in details if p.stem.isdigit()]) == 2


def test_snapshot_continues_when_one_item_fails(tmp_path: Path, settings, cache):
    class FlakyClient(FakeClient):
        def get_html(self, url, *, timeout=None):
            if "/tag/" in url:
                raise RuntimeError("blocked")
            return super().get_html(url, timeout=timeout)

    from douban_api.service import DoubanService

    service = DoubanService(settings, cache=cache, client=FlakyClient())  # type: ignore[arg-type]
    report = build_snapshot(service, tmp_path, tags=["小说"], details=0)

    assert report.errors
    assert report.books == 20
    assert (tmp_path / "api" / "v1" / "books" / "latest.json").exists()
