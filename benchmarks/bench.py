"""离线 / 联网基准测试。

用法::

    python -m benchmarks.bench --iterations 30          # 离线（fixture）
    python -m benchmarks.bench --iterations 10 --live   # 额外访问豆瓣测真实延迟

输出 Markdown 表格 + ``benchmarks/results.json``。
"""

from __future__ import annotations

import argparse
import gzip
import json
import platform
import statistics
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from benchmarks import legacy  # noqa: E402

from douban_api import parsers  # noqa: E402
from douban_api.app import create_app  # noqa: E402
from douban_api.cache import TTLCache  # noqa: E402
from douban_api.config import Settings  # noqa: E402
from douban_api.http import get_client  # noqa: E402
from douban_api.service import DoubanService, extract_search_data  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def timeit(fn, iterations: int = 20) -> dict[str, float]:
    fn()  # 预热
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - started) * 1000)
    return {
        "median_ms": round(statistics.median(samples), 3),
        "min_ms": round(min(samples), 3),
        "p95_ms": round(sorted(samples)[max(0, int(len(samples) * 0.95) - 1)], 3),
    }


def bench_parsing(iterations: int) -> list[dict]:
    rows: list[dict] = []
    cases = [
        ("最新图书列表", "latest.html", legacy.parse_latest, parsers.parse_latest),
        ("标签图书列表", "tag.html", legacy.parse_tag, parsers.parse_tag),
        ("图书详情页", "detail.html", legacy.parse_detail, parsers.parse_detail),
    ]
    for label, fixture, old_fn, new_fn in cases:
        page = read(fixture)
        old_error = None
        try:
            old = timeit(lambda page=page, fn=old_fn: fn(page), iterations)
        except Exception as exc:
            old_error = f"{exc.__class__.__name__}: {exc}"
            old = {"median_ms": None, "min_ms": None, "p95_ms": None}
        new = timeit(lambda page=page, fn=new_fn: fn(page), iterations)
        rows.append(
            {
                "case": label,
                "old_ms": old["median_ms"],
                "new_ms": new["median_ms"],
                "old_error": old_error,
                "speedup": round(old["median_ms"] / new["median_ms"], 2)
                if old["median_ms"]
                else None,
            }
        )
    # 纯正则扫描 vs 完整 XPath 解析
    page = read("tag.html")
    scan = timeit(lambda: legacy.legacy_scan(page), iterations)
    rows.append(
        {
            "case": "标签页：整页正则扫描 vs lxml 解析",
            "old_ms": scan["median_ms"],
            "new_ms": timeit(lambda: parsers.parse_tag(page), iterations)["median_ms"],
            "old_error": None,
            "speedup": None,
        }
    )
    return rows


def bench_search_decode(iterations: int) -> dict:
    page = read("search.html")
    new = timeit(lambda: parsers.parse_search_payload(extract_search_data(page)), iterations)
    result = {"new_ms": new["median_ms"], "old_ms": None, "old_error": None}

    payload = read("legacy_payload.txt").strip()
    legacy_new = timeit(
        lambda: extract_search_data(f'<script>window.__DATA__ = "{payload}";</script>'), 3
    )
    result["legacy_fallback_ms"] = legacy_new["median_ms"]

    try:
        import quickjs  # noqa: F401

        result["quickjs_available"] = True
    except ImportError:
        result["quickjs_available"] = False

    try:
        import execjs

        source = (ROOT / "src" / "douban_api" / "assets" / "legacy_decrypt.js").read_text(
            encoding="utf-8"
        )
        ctx = execjs.compile(source)
        result["old_ms"] = timeit(lambda: ctx.call("decrypt", payload), 3)["median_ms"]
    except Exception as exc:
        result["old_error"] = f"{exc.__class__.__name__}: {exc}"
    return result


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    body = json.dumps({"hello": "world", "padding": "x" * 2000}).encode()

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args) -> None:
        pass


def bench_http(iterations: int) -> dict:
    import requests

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    try:
        old = timeit(lambda: requests.get(url, timeout=5).content, iterations * 3)
        session = requests.Session()
        session.get(url, timeout=5)  # 建立连接
        new = timeit(lambda: session.get(url, timeout=5).content, iterations * 3)
        session.close()
    finally:
        server.shutdown()
        server.server_close()
    return {
        "old_ms": old["median_ms"],
        "new_ms": new["median_ms"],
        "speedup": round(old["median_ms"] / new["median_ms"], 2),
    }


def bench_cache(iterations: int) -> dict:
    import itertools

    cache = TTLCache(maxsize=4096, default_ttl=300)
    cache.set("k", {"books": [1, 2, 3]}, 300)
    hit = timeit(lambda: cache.get_or_load("k", 300, lambda: {"books": []}), iterations * 200)
    counter = itertools.count()

    def miss_once():
        key = f"fresh-{next(counter)}"
        return cache.get_or_load(key, 300, lambda: {"books": [1]})

    miss = timeit(miss_once, 100)
    return {
        "hit_us": round(hit["median_ms"] * 1000, 2),
        "miss_us": round(miss["median_ms"] * 1000, 2),
    }


def bench_gzip(iterations: int) -> dict:
    payload = json.dumps(parsers.parse_latest(read("latest.html")), ensure_ascii=False).encode()
    compressed = gzip.compress(payload, compresslevel=6)
    cost = timeit(lambda: gzip.compress(payload, compresslevel=6), iterations)
    return {
        "raw_kb": round(len(payload) / 1024, 1),
        "gzip_kb": round(len(compressed) / 1024, 1),
        "ratio": round(len(compressed) / len(payload), 3),
        "ms": cost["median_ms"],
    }


class _FakeClient:
    stats: ClassVar[dict[str, int]] = {
        "requests": 0,
        "failures": 0,
        "retries_exhausted": 0,
        "bytes": 0,
    }

    def get_html(self, url: str, *, timeout=None):
        from douban_api.http import FetchResult

        self.stats["requests"] += 1
        if "/tag/" in url:
            return FetchResult(read("tag.html"), 200, 0.0, url)
        return FetchResult(read("latest.html"), 200, 0.0, url)

    def close(self) -> None:
        pass


def bench_app(iterations: int) -> dict:
    settings = Settings(rate_limit_rpm=0, ttl_tag=600, use_orjson=False)
    service = DoubanService(settings, cache=TTLCache(), client=_FakeClient())  # type: ignore[arg-type]
    app = create_app(settings, service=service)
    app.config.update(TESTING=True)
    client = app.test_client()
    started = time.perf_counter()
    service.latest("全部", None)  # 首次：抓取 + 解析
    cold_ms = (time.perf_counter() - started) * 1000
    warm = timeit(lambda: client.get("/api/v1/books/tag?tag=小说"), iterations * 20)
    return {"cold_ms": round(cold_ms, 3), "warm_ms": warm["median_ms"]}


def bench_live(iterations: int) -> dict:
    import requests

    url = "https://book.douban.com/latest?subcat=%E5%85%A8%E9%83%A8&p=0"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    client = get_client(Settings())

    def old_flow():
        response = requests.get(url, headers=headers, timeout=15)
        return legacy.parse_latest(response.text)

    def new_flow():
        return parsers.parse_latest(client.get_html(url).text)

    def new_flow_with_cache():
        settings = Settings(ttl_latest=300)
        service = DoubanService(settings, cache=TTLCache(), client=None)  # 真实网络
        return service.latest("全部", None)

    result: dict = {}
    try:
        result["old"] = timeit(old_flow, iterations)
    except Exception as exc:
        result["old_error"] = f"{exc.__class__.__name__}: {exc}"
    try:
        result["new"] = timeit(new_flow, iterations)
    except Exception as exc:
        result["new_error"] = f"{exc.__class__.__name__}: {exc}"

    service = DoubanService(Settings(), cache=TTLCache(), client=None)
    started = time.perf_counter()
    service.latest("全部", None)
    first_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    service.latest("全部", None)
    warm_ms = (time.perf_counter() - started) * 1000
    result["service_first_ms"] = round(first_ms, 1)
    result["service_warm_ms"] = round(warm_ms, 2)
    return result


def render_markdown(results: dict) -> str:
    lines = [
        "# 基准测试结果",
        "",
        f"- 运行环境：{results['env']['python']} / {results['env']['platform']}",
        f"- 时间：{results['env']['timestamp']}",
        "",
        "## 解析（同一份真实豆瓣 HTML）",
        "",
        "| 场景 | 旧实现 (ms) | 新实现 (ms) | 提升 | 旧实现结果 |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in results["parsing"]:
        old = f"{row['old_ms']:.2f}" if row["old_ms"] is not None else "—"
        new = f"{row['new_ms']:.2f}"
        speedup = f"{row['speedup']:.2f}x" if row.get("speedup") else "—"
        note = "成功" if not row["old_error"] else f"失败：{row['old_error']}"
        lines.append(f"| {row['case']} | {old} | {new} | {speedup} | {note} |")

    http = results["http"]
    lines += [
        "",
        "## 上游 HTTP 连接复用（本地 keep-alive 服务，含完整请求）",
        "",
        "| 场景 | 每次新建连接 (ms) | Session 复用 (ms) | 提升 |",
        "| --- | ---: | ---: | ---: |",
        f"| 连续 60 次 GET | {http['old_ms']:.3f} | {http['new_ms']:.3f} | {http['speedup']:.2f}x |",
    ]

    cache = results["cache"]
    lines += [
        "",
        "## 缓存",
        "",
        f"- 命中：**{cache['hit_us']:.1f} µs/次**（纯内存字典 + LRU）",
        f"- 未命中（调用 loader）：{cache['miss_us']:.1f} µs/次",
    ]

    gz = results["gzip"]
    lines += [
        "",
        "## gzip",
        "",
        f"- 原始 JSON {gz['raw_kb']} KB → gzip {gz['gzip_kb']} KB（{gz['ratio'] * 100:.1f}%，"
        f"压缩耗时 {gz['ms']:.2f} ms）",
    ]

    app = results["app"]
    lines += [
        "",
        "## API 端到端（fixture 上游，Flask test client）",
        "",
        f"- 冷请求（抓取 + 解析）：{app['cold_ms']:.2f} ms",
        f"- 命中缓存：{app['warm_ms']:.3f} ms",
    ]

    search = results["search"]
    lines += [
        "",
        "## 搜索数据解码",
        "",
        "| 实现 | 耗时 |",
        "| --- | ---: |",
    ]
    if search.get("old_ms"):
        lines.append(f"| 旧版 execjs（每次 fork Node 进程） | {search['old_ms']:.1f} ms |")
    lines.append(f"| 新版 JSON 直读（当前豆瓣格式） | {search['new_ms']:.3f} ms |")
    lines.append(f"| 新版 quickjs 回退（旧版加密数据） | {search['legacy_fallback_ms']:.2f} ms |")
    if search.get("old_error"):
        lines.append(f"| 旧版 execjs 不可用 | {search['old_error']} |")

    live = results.get("live")
    if live:
        lines += ["", "## 联网实测（访问真实豆瓣）", ""]
        if "old" in live:
            lines.append(f"- 旧流程（新建连接 + 正则）：{live['old']['median_ms']:.1f} ms")
        if "old_error" in live:
            lines.append(f"- 旧流程失败：{live['old_error']}")
        if "new" in live:
            lines.append(f"- 新流程（连接复用 + lxml）：{live['new']['median_ms']:.1f} ms")
        if "new_error" in live:
            lines.append(f"- 新流程失败：{live['new_error']}")
        lines.append(f"- 服务层首次请求：{live['service_first_ms']} ms")
        lines.append(f"- 服务层缓存命中：{live['service_warm_ms']} ms")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--out", default=str(ROOT / "benchmarks"))
    args = parser.parse_args(argv)

    from datetime import datetime, timezone

    results: dict = {
        "env": {
            "python": platform.python_version(),
            "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
        "parsing": bench_parsing(args.iterations),
        "search": bench_search_decode(args.iterations),
        "http": bench_http(args.iterations),
        "cache": bench_cache(args.iterations),
        "gzip": bench_gzip(args.iterations),
        "app": bench_app(args.iterations),
    }
    if args.live:
        results["live"] = bench_live(max(3, args.iterations // 3))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown = render_markdown(results)
    (out / "results.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
