# GitHub Pages（静态 API + 文档）

GitHub Pages 只能托管静态文件，无法运行 Python。因此这里把"API"拆成两部分：

1. **文档站**：MkDocs Material 构建，包含 OpenAPI 参考与在线演练场；
2. **静态快照 API**：`pages.yml` 定时把热门查询抓取成 JSON，随站点一起发布。

## 静态 API 的形态

```text
https://<用户>.github.io/douban-request-api/
├── index.html                     # 文档首页
├── openapi.json                   # OpenAPI 3.1 规范
├── playground/                    # 在线演练场
└── api/v1/
    ├── index.json                 # 快照清单（可用端点、生成时间）
    ├── health.json                # {"status":"ok","mode":"snapshot"}
    ├── books/latest.json          # 最新图书（第 0 页）
    ├── books/tag/小说.json         # 各热门标签第 1 页
    ├── books/2567698.json         # 详情（前 N 本）
    └── search/index.json          # 浏览器端搜索索引
```

示例：

```bash
curl -s https://trueWangSyutung.github.io/douban-request-api/api/v1/books/latest.json | jq '.books[0].name'
curl -s https://trueWangSyutung.github.io/douban-request-api/api/v1/health.json
```

## 快照是怎么生成的

`pages.yml` 的流程：

```mermaid
flowchart LR
    A[checkout] --> B[安装依赖]
    B --> C[校验 OpenAPI]
    C --> D[mkdocs build]
    D --> E[恢复上次快照缓存]
    E --> F[douban-api snapshot]
    F --> G[合并进 site/]
    G --> H[upload-pages-artifact]
    H --> I[deploy-pages]
```

- 触发条件：`push`（`master`）、`schedule`（每 6 小时）、`workflow_dispatch`；
- 抓取失败不会导致部署失败：`snapshot` 步骤 `continue-on-error`，保留上一次成功的缓存，
  站点继续可用；
- 快照数据通过 `actions/cache` 在多次运行之间复用；仓库里的 `data/` 只是一份种子数据，
  用于首次部署或缓存被清理时兜底。

## 浏览器端使用

```html
<script type="module">
  const base = "https://<用户>.github.io/douban-request-api/api/v1";

  // 最新图书
  const latest = await (await fetch(`${base}/books/latest.json`)).json();

  // 详情
  const book = await (await fetch(`${base}/books/2567698.json`)).json();

  // 搜索：拉索引后本地过滤
  const index = await (await fetch(`${base}/search/index.json`)).json();
  const hits = index.books.filter((b) =>
    `${b.name} ${b.info} ${b.auther}`.toLowerCase().includes("三体")
  );
</script>
```

CORS 不需要额外配置：同源请求即可；静态文件默认带 `Access-Control-Allow-Origin: *`。

## 局限性

| 限制 | 说明 |
| --- | --- |
| 非实时 | 每 6 小时刷新一次 |
| 覆盖有限 | 只包含最新图书、固定标签列表、前 N 本详情 |
| 搜索近似 | 只能对索引做子串匹配，不是豆瓣的完整搜索 |
| 无分页 | 每个标签只保留第 1 页 |

需要实时/完整能力，请使用 [Cloudflare Worker](worker.md) 或 [Docker](docker.md)。

## 本地预览站点

```bash
pip install -r requirements-docs.txt
python -m douban_api openapi                 # 生成 docs/openapi.json
python -m douban_api snapshot --out site --details 10
mkdocs serve                                  # http://127.0.0.1:8000/douban-request-api/
```

> 本地的 `/api/v1/*.json` 需要把快照输出到 `site/api/v1`，与 `mkdocs build` 的产物合并后
> 用静态服务器预览；线上由 workflow 完成合并。
