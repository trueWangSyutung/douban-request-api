# 豆瓣图书查询 API

[![ci](https://github.com/trueWangSyutung/douban-request-api/actions/workflows/ci.yml/badge.svg)](https://github.com/trueWangSyutung/douban-request-api/actions/workflows/ci.yml)
[![pages](https://github.com/trueWangSyutung/douban-request-api/actions/workflows/pages.yml/badge.svg)](https://github.com/trueWangSyutung/douban-request-api/actions/workflows/pages.yml)
[![worker](https://github.com/trueWangSyutung/douban-request-api/actions/workflows/worker.yml/badge.svg)](https://github.com/trueWangSyutung/douban-request-api/actions/workflows/worker.yml)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![license](https://img.shields.io/badge/license-MIT-green)](license)

基于 Flask + lxml 的豆瓣图书查询 API。v2 重写了抓取、解析、缓存和部署链路：
**单次请求 1017ms → 231ms，缓存命中 ~10µs**，并提供 GitHub Pages 静态 API、文档站、
Cloudflare Worker 边缘 API 与 Docker 镜像四种交付形态。

> ⚠️ 仅供学习研究。数据版权归豆瓣所有，请勿高频遍历或商用。接口默认限流 120 次/分钟。

## 在线地址

| 内容 | 地址 | 状态 |
| --- | --- | --- |
| 📖 文档站（在线体验 / OpenAPI） | <https://trueWangSyutung.github.io/douban-request-api/> | ✅ 自动部署 |
| ⚡ 实时 API（Worker） | <https://bookapi.oaixiv.org> | ✅ 已上线 |
| 🗂️ 静态快照 API（只读） | `https://trueWangSyutung.github.io/douban-request-api/api/v1/` | ✅ 每 6 小时刷新 |
| 🐳 容器镜像 | `ghcr.io/truewangSyutung/douban-request-api:latest` | ✅ 自动构建 |

```bash
# 实时 API（Cloudflare Worker + 自定义域名）
curl -s "https://bookapi.oaixiv.org/api/v1/search?q=三体" | jq '.books[0].name'
curl -s "https://bookapi.oaixiv.org/api/v1/books/2567698" | jq '.book.score'

# 静态快照（GitHub Pages，只读）
curl -s "https://trueWangSyutung.github.io/douban-request-api/api/v1/books/latest.json" | jq '.books[0].name'
```

GitHub Pages 不能运行 Python，所以 Pages 上提供的是**定时快照 JSON**；实时/任意关键词
搜索由 Cloudflare Worker 提供，也可以用自己的服务器跑 Docker 镜像。

## 性能

| 场景 | v1 | v2 | 变化 |
| --- | ---: | ---: | ---: |
| 最新图书（真实豆瓣，冷请求） | 1017 ms | **231 ms** | 4.4× |
| 列表页解析（同一份 HTML） | 485 ms | **3.2 ms** | 151× |
| 搜索数据解码 | 62 ms | **0.10 ms** | 645× |
| 缓存命中（服务层） | — | **~10 µs** | — |
| 响应体积（gzip） | 8.8 KB | **2.1 KB** | −76% |

旧版正则解析在当前的标签页/详情页上会直接 `IndexError`——不只是慢，而是已经不可用。
完整数据与复现命令见 [性能文档](docs/performance.md)。

<details>
<summary>优化做了什么</summary>

1. **连接复用**：`requests.get` → 进程级 `Session` + 连接池 + 幂等 GET 重试；
2. **解析重写**：整页正则 → lxml XPath，按语义识别作者/出版社/年份/价格；
3. **去掉 PyExecJS**：搜索数据已是明文 JSON，`json.loads` 取代 fork Node 进程；
   旧加密格式由内置 quickjs 兜底；
4. **缓存**：TTL + LRU + 单飞合并 + 过期兜底，可选 Redis L2；
5. **传输**：gzip、`ETag`/`304`、`Cache-Control: stale-while-revalidate`；
6. **防护**：参数校验前置、令牌桶限流、上游超时与错误码映射。

</details>

## 快速开始

```bash
git clone https://github.com/trueWangSyutung/douban-request-api.git
cd douban-request-api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[server]"
python -m douban_api serve --port 5000
```

打开 <http://127.0.0.1:5000> 查看接口索引，<http://127.0.0.1:5000/docs> 是 Swagger UI。

```bash
curl -s "http://127.0.0.1:5000/api/v1/search?q=三体" | jq '.books[0]'
```

Docker：

```bash
docker build -t douban-api . && docker run --rm -p 8080:8080 douban-api
# 或
docker run --rm -p 8080:8080 ghcr.io/truewangSyutung/douban-request-api:latest
```

## 接口

| 方法 | 路径 | 说明 | 缓存 |
| --- | --- | --- | ---: |
| `GET` | `/api/v1/books/latest` | 最新图书 `?type=全部&page=0` | 300s |
| `GET` | `/api/v1/books/tag` | 标签图书 `?tag=小说&page=1` | 600s |
| `GET` | `/api/v1/books/{id}` | 图书详情 `/{id}` | 1800s |
| `GET` | `/api/v1/search` | 关键词搜索 `?q=三体` | 600s |
| `GET` | `/healthz` · `/metrics` | 健康检查 · 运行指标 | — |

旧路径 `/getNewBook`、`/getType`、`/getBookDetail`、`/search` 保持可用（deprecated）。

<details>
<summary>响应示例</summary>

```json
{
  "code": 200,
  "books": [
    {
      "id": "2567698",
      "name": "三体 : “地球往事”三部曲之一",
      "cover": "https://img3.doubanio.com/view/subject/m/public/s2768378.jpg",
      "info": "刘慈欣 / 重庆出版社 / 2008-1 / 23.00",
      "comment_count": 519247,
      "rating": 8.9,
      "url": "https://book.douban.com/subject/2567698/"
    }
  ],
  "meta": { "cached": false, "elapsed_ms": 231.4, "ttl": 600, "version": "2.0.0" }
}
```

错误统一为 `{"code": 10020, "msg": "参数错误"}`，错误码见
[接口概览](docs/api/index.md#通用约定)。

</details>

## 部署

### 1. GitHub Pages（文档 + 静态 API，零配置）

合并到 `master` 即触发 [`.github/workflows/pages.yml`](.github/workflows/pages.yml)：
`pytest → mkdocs build → 抓取快照 → upload-pages-artifact → deploy-pages`，
并用 `actions/cache` 在多次运行之间保留快照。首次需要在
**Settings → Pages → Source** 选择 **GitHub Actions**。

产物：

```text
https://<用户>.github.io/douban-request-api/
├── index.html                  # 文档
├── openapi.json                # OpenAPI 3.1
├── playground/                 # 在线演练场（默认调用静态 API）
└── api/v1/
    ├── index.json              # 快照清单
    ├── books/latest.json
    ├── books/tag/小说.json
    ├── books/2567698.json
    └── search/index.json       # 供浏览器端过滤
```

### 2. Cloudflare Worker（实时 API，一键）

当前已部署在 **<https://bookapi.oaixiv.org>**：Cloudflare Route
`bookapi.oaixiv.org/*` → `douban-request-api`（配置见
[`worker/wrangler.toml`](worker/wrangler.toml)）。

1. Cloudflare 创建 API Token（*Edit Cloudflare Workers* 模板）；
2. 仓库 Secrets 添加 `CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`；
3. 仓库 Variables 添加 `ENABLE_WORKER_DEPLOY = true`；
4. push 修改 `worker/**`，或手动运行 `worker` workflow。

详见 [部署文档](docs/deployment/worker.md)。Worker 版本已在本地用 `wrangler dev`
对真实豆瓣验证：路由、字段、缓存命中（`X-Cache: HIT`，~1ms）均正常。

### 3. Docker / 自建服务器

```bash
docker run -d --name douban-api -p 8080:8080 \
  -e REDIS_URL=redis://redis:6379/0 \
  ghcr.io/truewangSyutung/douban-request-api:latest
```

或 `gunicorn -c gunicorn.conf.py douban_api.app:create_app()`。详见
[Docker 部署](docs/deployment/docker.md)。

## 配置

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `PORT` / `HOST` | `5000` / `0.0.0.0` | 监听 |
| `TTL_LATEST` / `TTL_TAG` / `TTL_DETAIL` / `TTL_SEARCH` | `300` / `600` / `1800` / `600` | 缓存秒数，0 关闭 |
| `REDIS_URL` | 空 | 启用 L1 内存 + L2 Redis |
| `RATE_LIMIT_RPM` | `120` | 单 IP 每分钟请求数 |
| `HTTP_RETRIES` / `CONNECT_TIMEOUT` / `READ_TIMEOUT` | `2` / `3.5` / `7.0` | 上游重试与超时 |
| `GZIP_MIN_SIZE` / `CORS_ORIGINS` / `PUBLIC_CACHE` | `512` / `*` / `true` | 传输层 |
| `TRUST_PROXY` | `false` | 反向代理后按 `X-Forwarded-For` 限流 |
| `WARMUP` | `false` | 启动预热 |

完整列表见 [快速开始](docs/quickstart.md#配置项)。

## 项目结构

```text
├── src/douban_api/          # 核心包
│   ├── app.py               # Flask 工厂：路由 / gzip / ETag / CORS / 限流
│   ├── cache.py             # TTL + LRU + 单飞 + stale 兜底（可选 Redis）
│   ├── http.py              # Session 连接池 + 重试 + 超时
│   ├── parsers.py           # lxml XPath 解析
│   ├── service.py           # 编排：校验 → 缓存 → 抓取 → 解析
│   ├── snapshot.py          # 静态 API 快照导出
│   └── openapi.py           # OpenAPI 3.1（唯一来源）
├── worker/                  # Cloudflare Worker（实时边缘 API）
├── docs/                    # MkDocs Material 文档站
├── tests/                   # 60 个离线测试（真实 HTML fixture）
├── benchmarks/              # 新旧实现基准
├── .github/workflows/       # ci / pages / worker / docker
├── Dockerfile · gunicorn.conf.py · mkdocs.yml
└── api.py                   # 兼容入口：python api.py
```

## 开发

```bash
pip install -e ".[dev,server,legacy]"
ruff check . && ruff format --check .
pytest -q                       # 全部离线，不访问豆瓣
python -m benchmarks.bench --iterations 12 --live
mkdocs serve                    # 本地预览文档
```

CI 会在 Python 3.10 / 3.12 上跑 lint、测试（覆盖率 ≥70%）、OpenAPI 一致性校验、
真实启动冒烟测试与 Docker 构建。

## 免责声明

本项目不存储任何豆瓣数据，所有内容实时来自公开页面，仅用于技术学习。
请遵守豆瓣的用户协议与 `robots.txt`，控制访问频率；因使用本项目产生的任何后果由使用者自负。

## License

[MIT](license) © 2022-2026 Wang Xudong
