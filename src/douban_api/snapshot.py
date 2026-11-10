"""把线上数据导出为静态 JSON，供 GitHub Pages 只读 API 使用。

GitHub Pages 只能托管静态文件，因此这里把"最常被访问的查询"预热成 JSON：
最新图书、若干热门标签、这些书里的详情，以及一份可用于浏览器端搜索的索引。
定时任务（.github/workflows/pages.yml）会刷新这些文件。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .service import DoubanService
from .version import __version__

logger = logging.getLogger(__name__)

DEFAULT_TAGS = [
    "小说",
    "历史",
    "科幻",
    "文学",
    "心理学",
    "经典",
    "传记",
    "哲学",
    "经济学",
    "社会学",
]


@dataclass
class SnapshotReport:
    generated_at: str
    files: int = 0
    books: int = 0
    details: int = 0
    tags: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "files": self.files,
            "books": self.books,
            "details": self.details,
            "tags": self.tags,
            "errors": self.errors,
        }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: Any) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1


def _safe_name(tag: str) -> str:
    return tag.replace("/", "_").replace("\\", "_").strip() or "tag"


def build_snapshot(
    service: DoubanService,
    out_dir: str | Path,
    *,
    tags: list[str] | None = None,
    details: int = 30,
) -> SnapshotReport:
    out = Path(out_dir)
    api = out / "api" / "v1"
    generated_at = _now()
    report = SnapshotReport(generated_at=generated_at)
    tags = tags or DEFAULT_TAGS
    index_docs: dict[str, dict[str, Any]] = {}

    def remember(books: list[dict[str, Any]]) -> None:
        for book in books:
            subject_id = str(book.get("id") or "")
            if not subject_id or subject_id in index_docs:
                continue
            index_docs[subject_id] = {
                "id": subject_id,
                "name": book.get("name", ""),
                "info": book.get("info", ""),
                "cover": book.get("cover", ""),
                "auther": book.get("auther", ""),
                "rating": book.get("comment") or book.get("rating") or "",
                "rating_count": book.get("rating_count") or book.get("comment_count") or "",
                "url": book.get("url", ""),
            }
            report.books += 1

    # 1) 最新图书
    try:
        payload, _ = service.latest("全部", None)
        payload["meta"] = {"generated_at": generated_at, "source": "snapshot"}
        report.files += _write_json(api / "books" / "latest.json", payload)
        remember(payload.get("books", []))
    except Exception as exc:
        report.errors.append(f"latest: {exc}")
        logger.warning("最新图书快照失败：%s", exc)

    # 2) 标签页
    for tag in tags:
        try:
            payload, _ = service.tag(tag, "1")
            payload["meta"] = {"generated_at": generated_at, "source": "snapshot"}
            report.files += _write_json(api / "books" / "tag" / f"{_safe_name(tag)}.json", payload)
            report.tags.append(tag)
            remember(payload.get("books", []))
        except Exception as exc:
            report.errors.append(f"tag {tag}: {exc}")
            logger.warning("标签 %s 快照失败：%s", tag, exc)

    # 3) 详情（只抓有评分/最新的前 N 本，避免给豆瓣造成压力）
    for subject_id in list(index_docs)[: max(0, details)]:
        try:
            payload, _ = service.detail(subject_id)
            payload["meta"] = {"generated_at": generated_at, "source": "snapshot"}
            report.files += _write_json(api / "books" / f"{subject_id}.json", payload)
            report.details += 1
            book = payload.get("book", {})
            if subject_id in index_docs:
                index_docs[subject_id]["auther"] = (
                    book.get("auther") or index_docs[subject_id]["auther"]
                )
                index_docs[subject_id]["rating"] = (
                    book.get("score") or index_docs[subject_id]["rating"]
                )
                index_docs[subject_id]["rating_count"] = (
                    book.get("score_num") or index_docs[subject_id]["rating_count"]
                )
        except Exception as exc:
            report.errors.append(f"detail {subject_id}: {exc}")

    # 4) 浏览器端搜索索引
    report.files += _write_json(
        api / "search" / "index.json",
        {
            "generated_at": generated_at,
            "count": len(index_docs),
            "books": list(index_docs.values()),
        },
    )

    # 5) 清单 + 健康检查
    report.files += _write_json(
        api / "index.json",
        {
            "name": "豆瓣图书查询 API - 静态快照",
            "version": __version__,
            "generated_at": generated_at,
            "note": "GitHub Pages 只提供只读快照；实时接口请使用 Cloudflare Worker 或自建服务。",
            "tags": report.tags,
            "details": report.details,
            "books": report.books,
            "endpoints": {
                "latest": "books/latest.json",
                "tag": "books/tag/{tag}.json",
                "detail": "books/{id}.json",
                "search_index": "search/index.json",
            },
        },
    )
    report.files += _write_json(
        api / "health.json",
        {"status": "ok", "mode": "snapshot", "version": __version__, "generated_at": generated_at},
    )
    return report
