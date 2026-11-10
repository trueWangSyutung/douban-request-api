from __future__ import annotations

import json

import pytest

from douban_api import parsers
from douban_api.errors import ParseError
from douban_api.service import decrypt_legacy, extract_search_data

from .conftest import read_fixture


def test_parse_latest():
    books = parsers.parse_latest(read_fixture("latest.html"))
    assert len(books) == 20
    first = books[0]
    assert first["id"] == "38613720"
    assert first["name"] == "空地"
    assert first["auther"] == "李颖迪"
    assert first["publisher"] == "文汇出版社"
    assert first["price"] == "59.00"
    assert first["comment"] == "8.3"
    assert first["rating_count"] == "227"
    assert first["url"].endswith("/subject/38613720/")


def test_parse_tag():
    books = parsers.parse_tag(read_fixture("tag.html"))
    assert len(books) == 20
    first = books[0]
    assert first["id"] == "38370177"
    assert first["info"].startswith("马伯庸")
    assert first["comment"] == "6.7"
    assert first["rating_count"] == "5015"


def test_parse_detail():
    book = parsers.parse_detail(read_fixture("detail.html"))
    assert book["name"] == "三体"
    assert book["auther"] == "刘慈欣"
    assert book["authors"] == ["刘慈欣"]
    assert book["publisher"] == "重庆出版社"
    assert book["producer"] == "科幻世界"
    assert book["ISBN"] == "9787536692930"
    assert book["price"] == "23.00"
    assert book["score"] == "8.9"
    assert book["score_num"] == "519247"
    assert book["comment"]["star5"] == "62.6"
    assert set(book["comment"]) == {f"star{i}" for i in range(1, 6)}
    assert "红岸工程" in book["introduction"]
    assert "刘慈欣，祖籍河南" in book["auther_introduction"]
    assert book["info"]["出版年"] == "2008-1"


def test_parse_detail_requires_title():
    with pytest.raises(ParseError):
        parsers.parse_detail("<html><body>not a book page</body></html>")


def test_parse_empty_list_raises():
    with pytest.raises(ParseError):
        parsers.parse_tag("<html><body><ul></ul></body></html>")


def test_split_biblio_handles_reordered_fields():
    parsed = parsers.split_biblio("李颖迪 / 2026-10 / 文汇出版社 / 59.00 / 平装")
    assert parsed["auther"] == "李颖迪"
    assert parsed["publish_date"] == "2026-10"
    assert parsed["publisher"] == "文汇出版社"
    assert parsed["price"] == "59.00"
    assert parsed["binding"] == "平装"


def test_search_payload_is_plain_json():
    data = extract_search_data(read_fixture("search.html"))
    result = parsers.parse_search_payload(data)
    assert result["total"] == 250
    assert result["q"] == "三体"
    assert len(result["books"]) == 15
    assert result["books"][0]["id"] == "2567698"
    assert result["books"][0]["rating"] == 8.9
    assert result["series"][0]["name"].startswith("[丛书]")


def test_extract_search_data_missing_marker():
    with pytest.raises(ParseError):
        extract_search_data("<html><body>nothing</body></html>")


def test_legacy_decrypt_matches_expected():
    pytest.importorskip("quickjs")
    payload = (read_fixture("legacy_payload.txt")).strip()
    expected = json.loads(read_fixture("legacy_expected.json"))
    assert decrypt_legacy(payload) == expected


def test_legacy_payload_through_extract_search_data():
    pytest.importorskip("quickjs")
    payload = read_fixture("legacy_payload.txt").strip()
    page = f'<script>window.__DATA__ = "{payload}";</script>'
    data = extract_search_data(page)
    assert data["payload"]["total"] == 803
