# 更新日志

## v2.0.0

彻底重写抓取、解析与部署链路，保持接口向后兼容。

### 性能

- **连接复用**：进程级 `requests.Session` + 连接池 + 幂等 GET 重试，单次冷请求 1017ms → 231ms。
- **解析重写**：整页正则 → lxml XPath，最新图书解析 485ms → 3.2ms（151×）。
  旧正则已无法解析当前标签页与详情页（`IndexError`）。
- **搜索解码**：`execjs`（每次 fork Node，62ms）→ `json.loads`（0.1ms）；
  保留 quickjs 回退以兼容旧版加密数据。
- **缓存**：TTL + LRU、单飞合并、stale-while-error；可选 Redis L2。
- **传输**：gzip（JSON −76%）、`ETag`/`304`、`Cache-Control: stale-while-revalidate`。
- **限流**：单 IP 令牌桶，默认 120 rpm，超限返回 429 + `Retry-After`。

### 功能

- 新增 `/api/v1/books/latest`、`/api/v1/books/tag`、`/api/v1/books/{id}`、`/api/v1/search`；
  旧路径 `/getNewBook`、`/getType`、`/getBookDetail`、`/search` 继续可用。
- 新增 `/healthz`、`/metrics`、`/docs`（Swagger UI）、`/openapi.json`。
- 响应新增 `meta`（`cached`、`elapsed_ms`、`ttl`、`version`）与诊断响应头。
- 详情字段扩充：`authors[]`、`producer`、`publish_date`、`pages`、`binding`、
  `subtitle`、`original_title`、`translator`、`series`、`tags[]`、`info{}`。
- 搜索新增 `series[]`，并支持新版模板 `search_simple` / `search_more`。

### 部署

- `.github/workflows/ci.yml`：ruff + pytest（3.10/3.12）+ 覆盖率 + Docker 冒烟。
- `.github/workflows/pages.yml`：MkDocs 文档 + 静态快照 API，部署到 GitHub Pages，
  每 6 小时刷新。
- `.github/workflows/worker.yml`：Cloudflare Worker 测试与部署。
- `.github/workflows/docker.yml`：多架构镜像推送 GHCR。
- 新增 `Dockerfile`、`docker-compose.yml`、`gunicorn.conf.py`、`worker/`。

### 破坏性变化

- `main.js` 移至 `src/douban_api/assets/legacy_decrypt.js`（不再在仓库根目录提供）。
- `getType` 的 `comment` 字段现在只返回纯评分字符串（旧版可能返回 `"(5015人评价)"` 这类脏数据）。
- 网络错误返回 `502`（旧版是 500 + `code 200` 或直接抛栈）。
- 环境变量 `PORT`/`HOST` 仍然有效，新增 `REDIS_URL`、`RATE_LIMIT_RPM` 等（见快速开始）。
