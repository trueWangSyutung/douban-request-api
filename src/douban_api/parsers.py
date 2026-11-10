"""HTML / JSON 解析层。

相对旧版的关键变化：
* 用 lxml 的 XPath 定位结构，替代在整页 HTML 上反复 ``re.findall`` 与字符串替换
  （旧实现会因豆瓣改版或页面里出现注释而错位）；
* 旧正则把 ``\\s`` 当空格替换（``\\s`` 在普通字符串里其实是反斜杠+s），实际没有生效；
* 输出字段保持向后兼容：``auther``、``comment``、``info`` 等字段名不变。
"""

from __future__ import annotations

import re
from typing import Any

from lxml import etree, html

from .errors import ParseError

_PARSER = html.HTMLParser(recover=True, no_network=True, remove_comments=True, encoding="utf-8")
_WS_RE = re.compile(r"[\s\u3000\xa0]+")
_COUNT_RE = re.compile(r"(\d[\d,]*)\s*人(?:评价|评分)")
_SUBJECT_RE = re.compile(r"/subject/(\d{4,12})")
_PRICE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*元")
_YEAR_RE = re.compile(r"((?:19|20)\d{2}(?:[-/.]\d{1,2}){0,2})")

INFO_LABELS = (
    "作者",
    "译者",
    "出版社",
    "出品方",
    "出版年",
    "页数",
    "定价",
    "装帧",
    "ISBN",
    "副标题",
    "原作名",
    "丛书",
    "统一书号",
)


def clean(text: str | None) -> str:
    """去掉换行、制表符、全角空格与 NBSP，压缩连续空白。"""
    if not text:
        return ""
    return _WS_RE.sub(" ", text).strip()


def to_document(page: str) -> html.HtmlElement:
    try:
        doc = html.fromstring(page, parser=_PARSER)
    except (etree.ParserError, ValueError) as exc:  # pragma: no cover - 极端输入
        raise ParseError("上游页面无法解析") from exc
    if doc is None:
        raise ParseError("上游页面为空")
    return doc


def _first_text(nodes: Any) -> str:
    """取第一个节点/属性值的文本（XPath 结果可能是元素，也可能是字符串）。"""
    if not nodes:
        return ""
    first = nodes[0]
    if isinstance(first, str):
        return clean(first)
    return clean(first.text_content())


def _subject_id(href: str) -> str:
    match = _SUBJECT_RE.search(href or "")
    return match.group(1) if match else ""


def split_biblio(raw: str) -> dict[str, str]:
    """把 "作者 / 出版社 / 2008-1 / 23.00元" 这类出版信息拆成结构化字段。

    豆瓣不同页面的字段顺序并不一致（新版 latest 页是 作者/出版年/出版社/定价/装帧），
    因此按特征识别而不是按固定下标。
    """
    parts = [clean(p) for p in raw.split("/") if clean(p)]
    result: dict[str, str] = {
        "info": clean(raw),
        "auther": "",
        "publisher": "",
        "price": "",
        "publish_date": "",
        "binding": "",
    }
    if not parts:
        return result

    result["auther"] = parts[0]
    for part in parts[1:]:
        if not result["price"] and re.fullmatch(r"\d+(?:\.\d+)?\s*元?", part):
            result["price"] = _PRICE_RE.sub(r"\1", part) if "元" in part else part
            continue
        if not result["publish_date"] and _YEAR_RE.fullmatch(part):
            result["publish_date"] = part
            continue
        if not result["publisher"] and any(k in part for k in ("出版", "书局", "印书馆", "集团")):
            result["publisher"] = part
            continue
        if not result["binding"] and part in (
            "平装",
            "精装",
            "Hardcover",
            "Paperback",
            "Kindle",
            "电子书",
            "盒装",
        ):
            result["binding"] = part
    if not result["publisher"] and len(parts) >= 3:
        result["publisher"] = parts[2]
    return result


def _rating_from_item(node: html.HtmlElement) -> tuple[str, str]:
    """从列表项里取评分与评价人数（新旧版页面结构不同）。"""
    score = ""
    count = ""
    for span in node.xpath(
        './/span[contains(@class,"rating_nums") or contains(@class,"font-small")]'
    ):
        text = clean(span.text_content())
        if re.fullmatch(r"\d+(?:\.\d+)?", text):
            score = text
            break
    if not score:
        star = node.xpath('.//span[starts-with(@class,"allstar")]/@class')
        for cls in star:
            match = re.search(r"allstar(\d{2})", cls)
            if match:
                score = f"{int(match.group(1)) / 10:.1f}".rstrip("0").rstrip(".")
                break
    match = _COUNT_RE.search(clean(node.text_content()))
    if match:
        count = match.group(1).replace(",", "")
    return score, count


def parse_latest(page: str) -> list[dict[str, str]]:
    """解析 https://book.douban.com/latest 的图书列表。"""
    doc = to_document(page)
    books: list[dict[str, str]] = []
    for node in doc.xpath('//li[contains(@class,"media")]'):
        link = node.xpath('.//div[contains(@class,"media__img")]//a/@href') or node.xpath(
            ".//a/@href"
        )
        subject_id = _subject_id(link[0] if link else "")
        if not subject_id:
            continue
        cover = _first_text(
            node.xpath('.//img[contains(@class,"subject-cover")]/@src')
        ) or _first_text(node.xpath(".//img/@src"))
        name = _first_text(node.xpath(".//h2//a")) or _first_text(node.xpath(".//h2"))
        abstract = _first_text(node.xpath('.//p[contains(@class,"subject-abstract")]'))
        score, count = _rating_from_item(node)
        book: dict[str, str] = {"id": subject_id, "cover": cover, "name": name}
        book.update({k: v for k, v in split_biblio(abstract).items() if v})
        book["comment"] = score
        book["rating_count"] = count
        book["url"] = f"https://book.douban.com/subject/{subject_id}/"
        books.append(book)
    if not books:
        raise ParseError("未能在最新图书页解析到任何条目")
    return books


def parse_tag(page: str) -> list[dict[str, str]]:
    """解析 https://book.douban.com/tag/<tag> 的图书列表。"""
    doc = to_document(page)
    books: list[dict[str, str]] = []
    for node in doc.xpath('//li[contains(@class,"subject-item")]'):
        link = node.xpath(".//h2//a/@href") or node.xpath('.//a[contains(@class,"nbg")]/@href')
        subject_id = _subject_id(link[0] if link else "")
        if not subject_id:
            continue
        cover = _first_text(node.xpath(".//img/@src"))
        name = _first_text(node.xpath(".//h2//a")) or _first_text(node.xpath(".//h2"))
        info = _first_text(node.xpath('.//div[contains(@class,"pub")]'))
        score, count = _rating_from_item(node)
        books.append(
            {
                "id": subject_id,
                "cover": cover,
                "name": name,
                "info": info,
                "comment": score,
                "rating_count": count,
                "url": f"https://book.douban.com/subject/{subject_id}/",
            }
        )
    if not books:
        raise ParseError("未能在标签页解析到任何条目")
    return books


def _info_lines(node: html.HtmlElement) -> list[str]:
    """按 ``<br>`` 和 ``<span class="pl">`` 切分 #info，保留文本顺序。

    直接对 HTML 做正则去标签会踩坑：豆瓣源码里冒号与 ``<a>`` 之间常有换行和缩进，
    按换行切分会把"作者"和作者名拆成两行。
    """
    lines: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        text = clean("".join(buffer))
        if text:
            lines.append(text)
        buffer.clear()

    def is_label(element: Any) -> bool:
        return (
            element is not node
            and isinstance(element.tag, str)
            and element.tag == "span"
            and "pl" in (element.get("class") or "")
        )

    def walk(element: html.HtmlElement) -> None:
        if isinstance(element.tag, str) and element.tag == "br":
            flush()
            if element.tail:
                buffer.append(element.tail)
            return
        if is_label(element):
            flush()
        if isinstance(element.tag, str) and element.tag != "br" and element.text:
            buffer.append(element.text)
        for child in element:
            walk(child)
        if element is not node and element.tail:
            buffer.append(element.tail)

    walk(node)
    flush()
    return lines


def _info_block(doc: html.HtmlElement) -> dict[str, Any]:
    nodes = doc.xpath('//div[@id="info"]')
    if not nodes:
        return {}
    parsed: dict[str, Any] = {}
    authors: list[str] = []
    for line in _info_lines(nodes[0]):
        match = re.match(r"^([^:：]{1,12})\s*[:：]\s*(.*)$", line)
        if not match:
            continue
        label, value = clean(match.group(1)).rstrip(":："), clean(match.group(2))
        if not value:
            continue
        if label == "作者":
            authors.append(value)
        elif label in INFO_LABELS:
            parsed.setdefault(label, value)
    if authors:
        parsed["作者"] = " / ".join(authors)
    return parsed


def _intro_text(node: html.HtmlElement) -> str:
    paragraphs = [clean(p.text_content()) for p in node.xpath(".//p")]
    paragraphs = [p for p in paragraphs if p]
    if paragraphs:
        return "\n".join(paragraphs)
    text = clean(node.text_content())
    return re.sub(r"\(?展开全部\)?$", "", text).strip()


def _author_intro(doc: html.HtmlElement) -> str:
    for heading in doc.xpath("//h2"):
        if "作者简介" not in clean(heading.text_content()):
            continue
        sibling = heading.getnext()
        while sibling is not None:
            intros = sibling.xpath('.//div[contains(@class,"intro")]')
            if intros:
                return _intro_text(intros[0])
            sibling = sibling.getnext()
    intros = doc.xpath('//div[contains(@class,"intro")]')
    return _intro_text(intros[1]) if len(intros) > 1 else ""


def parse_detail(page: str) -> dict[str, Any]:
    """解析图书详情页 https://book.douban.com/subject/<id>/。"""
    doc = to_document(page)
    title = _first_text(doc.xpath('//h1//span[@property="v:itemreviewed"]')) or _first_text(
        doc.xpath("//h1//span")
    )
    if not title:
        raise ParseError("未能在详情页解析到书名，页面结构可能已变更")

    cover = _first_text(doc.xpath('//div[@id="mainpic"]//img/@src')) or _first_text(
        doc.xpath("//div[contains(@class,'article')]//img/@src")
    )

    info = _info_block(doc)
    authors = [a for a in clean(info.get("作者", "")).split(" / ") if a]

    score = _first_text(doc.xpath('//strong[@property="v:average"]'))
    votes = _first_text(doc.xpath('//span[@property="v:votes"]'))
    percents = doc.xpath('//span[@class="rating_per"]/text()')
    comment: dict[str, str] = {}
    for index, percent in enumerate(percents[:5], start=1):
        comment[f"star{6 - index}"] = clean(percent).replace("%", "")
    for star in range(1, 6):
        comment.setdefault(f"star{star}", "0")

    intro = ""
    intro_nodes = doc.xpath('//div[@id="link-report"]//div[contains(@class,"intro")]')
    if intro_nodes:
        intro = _intro_text(intro_nodes[0])
    tags = [
        clean(t)
        for t in doc.xpath(
            '//div[@id="db-tags-section"]//a/text() | //div[contains(@class,"tags")]//a/text()'
        )
        if clean(t)
    ]

    book: dict[str, Any] = {
        "name": title,
        "cover": cover,
        "auther": info.get("作者", ""),
        "authors": authors,
        "publisher": info.get("出版社", ""),
        "producer": info.get("出品方", ""),
        "publish_date": info.get("出版年", ""),
        "pages": info.get("页数", ""),
        "binding": info.get("装帧", ""),
        "price": _PRICE_RE.sub(r"\1", info.get("定价", "")).strip(),
        "ISBN": info.get("ISBN", ""),
        "subtitle": info.get("副标题", ""),
        "original_title": info.get("原作名", ""),
        "translator": info.get("译者", ""),
        "series": info.get("丛书", ""),
        "score": score or "0",
        "score_num": votes or "0",
        "comment": comment,
        "introduction": intro,
        "auther_introduction": _author_intro(doc),
        "tags": tags,
        "info": info,
    }
    return book


def parse_search_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """把豆瓣搜索页 ``window.__DATA__`` 结构转成 API 输出。"""
    if not isinstance(payload, dict):
        raise ParseError("搜索数据结构异常")
    if "items" not in payload and isinstance(payload.get("payload"), dict):
        payload = payload["payload"]
    items = payload.get("items") or []
    books: list[dict[str, Any]] = []
    series: list[dict[str, Any]] = []
    author: dict[str, Any] | None = None

    for item in items:
        if not isinstance(item, dict):
            continue
        tpl = item.get("tpl_name") or ""
        rating = item.get("rating") or {}
        if tpl in ("search_subject", "book", "search_simple_subject"):
            books.append(
                {
                    "id": str(item.get("id") or _subject_id(item.get("url", ""))),
                    "name": clean(item.get("title")),
                    "cover": item.get("cover_url") or "",
                    "info": clean(item.get("abstract")),
                    "comment_count": (rating or {}).get("count"),
                    "rating": (rating or {}).get("value"),
                    "url": item.get("url") or "",
                }
            )
        elif tpl in ("search_common", "search_author"):
            author = {
                "id": item.get("id"),
                "name": clean(item.get("title")),
                "info": clean(item.get("abstract_2") or item.get("abstract")),
                "img": item.get("cover_url") or "",
                "url": item.get("url") or "",
            }
        elif tpl in ("search_simple", "search_series"):
            series.append(
                {
                    "id": item.get("id"),
                    "name": clean(item.get("title")),
                    "info": clean(item.get("abstract")),
                    "url": item.get("url") or "",
                }
            )

    result: dict[str, Any] = {
        "books": books,
        "total": payload.get("total", len(books)),
        "q": clean(payload.get("text")) or None,
    }
    if author is not None:
        result["author"] = author
    if series:
        result["series"] = series
    return result
