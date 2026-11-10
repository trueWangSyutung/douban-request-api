"""命令行入口：``serve`` / ``snapshot`` / ``openapi``。"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

from .config import Settings
from .service import DoubanService
from .snapshot import DEFAULT_TAGS, build_snapshot
from .version import __version__

ROOT = Path(__file__).resolve().parents[2]
DOCS_OPENAPI = ROOT / "docs" / "openapi.json"


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _serve(args: argparse.Namespace) -> int:
    settings = Settings.from_env().with_overrides(
        host=args.host or os.getenv("HOST", "0.0.0.0"),
        port=args.port or int(os.getenv("PORT", "5000")),
        debug=args.debug,
    )
    from .app import create_app

    app = create_app(settings)

    if settings.warmup:

        def _warm() -> None:
            service: DoubanService = app.extensions["douban_service"]
            for call in (lambda: service.latest("全部", None), lambda: service.tag("小说", "1")):
                try:
                    call()
                except Exception as exc:
                    logging.getLogger(__name__).warning("预热失败：%s", exc)

        threading.Thread(target=_warm, name="warmup", daemon=True).start()

    if args.reload:
        app.run(host=settings.host, port=settings.port, debug=True, threaded=True)
        return 0

    try:
        from gunicorn.app.base import BaseApplication
    except ImportError:
        app.run(host=settings.host, port=settings.port, debug=settings.debug, threaded=True)
        return 0

    class _Application(BaseApplication):  # type: ignore[misc]
        def __init__(self, flask_app, options: dict) -> None:
            self._app = flask_app
            self._options = options
            super().__init__()

        def load_config(self) -> None:
            for key, value in self._options.items():
                if key in self.cfg.settings and value is not None:
                    self.cfg.set(key, value)

        def load(self):
            return self._app

    workers = args.workers or int(os.getenv("WEB_CONCURRENCY", "2"))
    _Application(
        app,
        {
            "bind": f"{settings.host}:{settings.port}",
            "workers": workers,
            "threads": args.threads or int(os.getenv("GUNICORN_THREADS", "8")),
            "worker_class": "gthread",
            "timeout": 30,
            "graceful_timeout": 20,
            "keepalive": 5,
            "accesslog": "-",
            "errorlog": "-",
            "loglevel": settings.log_level,
            "preload_app": True,
        },
    ).run()
    return 0


def _snapshot(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    service = DoubanService(settings)
    tags = args.tag or DEFAULT_TAGS
    report = build_snapshot(service, args.out, tags=tags, details=args.details)
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    if report.errors and not report.books:
        return 1
    return 0


def _openapi(args: argparse.Namespace) -> int:
    from .openapi import build_spec

    spec = build_spec()
    target = Path(args.out) if args.out else DOCS_OPENAPI
    rendered = json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if args.check:
        if not target.exists():
            print(f"缺少 {target}，请先运行：douban-api openapi", file=sys.stderr)
            return 1
        if target.read_text(encoding="utf-8") != rendered:
            print(f"{target} 已过期，请运行：douban-api openapi", file=sys.stderr)
            return 1
        print(f"{target} 与代码一致")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    print(f"已写入 {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="douban-api", description="豆瓣图书查询 API")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="启动 HTTP 服务（生产环境使用 gunicorn gthread）")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)
    serve.add_argument("--workers", type=int, default=None)
    serve.add_argument("--threads", type=int, default=None)
    serve.add_argument("--reload", action="store_true", help="开发模式（Flask 自带服务器）")
    serve.add_argument("--debug", action="store_true")
    serve.set_defaults(func=_serve)

    snapshot = sub.add_parser("snapshot", help="导出静态 JSON 快照（用于 GitHub Pages）")
    snapshot.add_argument("--out", default="site", help="输出目录（默认 site）")
    snapshot.add_argument("--tag", action="append", help="要抓取的标签，可重复")
    snapshot.add_argument("--details", type=int, default=30, help="抓取详情的图书数量")
    snapshot.set_defaults(func=_snapshot)

    openapi = sub.add_parser("openapi", help="导出 / 校验 OpenAPI 规范")
    openapi.add_argument("--out", default=None)
    openapi.add_argument("--check", action="store_true")
    openapi.set_defaults(func=_openapi)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        args = parser.parse_args(["serve"])
    _configure_logging(os.getenv("LOG_LEVEL", "info"))
    started = time.perf_counter()
    code = args.func(args)
    logging.getLogger("douban_api").debug("命令耗时 %.1fms", (time.perf_counter() - started) * 1000)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
