# 接口概览

- **Base URL（在线，实时）**：`https://bookapi.oaixiv.org`
- **Base URL（本地）**：`http://127.0.0.1:5000`
- **Base URL（Pages 快照）**：`https://trueWangSyutung.github.io/douban-request-api/api/v1`
- **协议**：仅 HTTPS/HTTP GET，无鉴权
- **编码**：UTF-8；响应默认 `application/json`，支持 `gzip`

## 通用约定

所有成功响应都包含 `code: 200`，业务数据在 `books` / `book` 等字段中，诊断信息在 `meta`：

```json
{
  "code": 200,
  "books": [],
  "meta": {
    "cached": true,
    "elapsed_ms": 0.42,
    "ttl": 600,
    "version": "2.0.0"
  }
}
```

错误响应统一为 `{"code": <业务码>, "msg": "<说明>"}`，HTTP 状态码表示类别：

| HTTP | code | 含义 |
| ---: | ---: | --- |
| 400 | 10020 | 参数错误/缺失 |
| 400 | 10021 | 参数为空 |
| 400 | 10022 | 页数小于等于 0 |
| 404 | 10040 | 图书/资源不存在 |
| 429 | 10050 | 触发限流（带 `Retry-After`） |
| 502 | 10030 | 上游请求失败或超时 |
| 502 | 10060 | 上游响应解析失败 |
| 500 | 10070 | 服务内部错误 |

## 图书列表

### 最新图书

```http
GET /api/v1/books/latest?type=全部&page=0
```

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `type` | 否 | 分类，默认 `全部`，取值见豆瓣最新图书页 |
| `page` | 否 | 从 **0** 开始，默认 0 |

返回 `books[]`，每项包含：`id`、`name`、`cover`、`url`、`info`、`auther`、`publisher`、
`publish_date`、`price`、`binding`、`comment`（评分）、`rating_count`。

### 标签图书

```http
GET /api/v1/books/tag?tag=小说&page=1
```

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `tag` | 是 | 标签名，最多 32 字符，例如 `小说`、`历史`、`科幻` |
| `page` | 否 | 从 **1** 开始，默认 1，每页 20 本 |

`books[]` 含 `id`、`name`、`cover`、`info`、`comment`、`rating_count`。

### 图书详情

```http
GET /api/v1/books/2567698
```

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `id` | 路径 | 4–12 位数字的豆瓣图书 ID |

`book` 字段：`name`、`cover`、`auther`、`authors[]`、`publisher`、`producer`、
`publish_date`、`pages`、`binding`、`price`、`ISBN`、`subtitle`、`original_title`、
`translator`、`series`、`score`、`score_num`、`comment.star1..star5`（百分比）、
`introduction`、`auther_introduction`、`tags[]`、`info`（原始键值对）。

## 搜索

```http
GET /api/v1/search?q=三体
```

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `q` | 是 | 关键词，最多 64 字符 |

返回：

- `books[]`：`id`、`name`、`cover`、`info`、`comment_count`、`rating`、`url`
- `series[]`（可选）：命中的丛书
- `author`（可选）：命中的作者
- `total`：豆瓣侧命中总数

!!! note "关于搜索数据的解密"
    v1 需要用 60KB 混淆 JS + PyExecJS 每个请求 fork 一个 Node 进程来解密
    `window.__DATA__`（约 60ms）。现在豆瓣直接返回明文 JSON，v2 用 `json.loads`
    解析（约 0.1ms）；仅当上游回退到旧格式时才启用内置的 quickjs 回退。

## 缓存与条件请求

| 响应头 | 说明 |
| --- | --- |
| `X-Cache` | `HIT` / `MISS` |
| `X-Response-Time` | 服务端处理耗时 |
| `X-Request-Id` | 请求追踪 ID |
| `ETag` | 弱 ETag，基于业务数据（不含 `meta`） |
| `Cache-Control` | `public, max-age=TTL/2, stale-while-revalidate=TTL` |
| `Vary` | 含 `Accept-Encoding` |

带 `If-None-Match` 命中时返回 `304 Not Modified`（无正文），可显著降低移动端流量。

```bash
ETAG=$(curl -sI "http://127.0.0.1:5000/api/v1/books/latest" | awk -F': ' '/^etag/{print $2}' | tr -d '\r')
curl -s -o /dev/null -w "%{http_code}\n" -H "If-None-Match: $ETAG" \
     "http://127.0.0.1:5000/api/v1/books/latest"
# 304
```

## 限流

默认 120 次/分钟/IP（令牌桶，允许短时突发）。响应头 `X-RateLimit-Remaining` 给出剩余额度，
超限返回 `429` + `Retry-After`。

## 系统接口

```bash
curl -s http://127.0.0.1:5000/healthz
# {"status":"ok","version":"2.0.0","uptime_s":12.3,"cache_backend":"memory"}

curl -s http://127.0.0.1:5000/metrics | jq .cache
# {"hit": 12, "miss": 3, "stale": 0, "evict": 0, "load": 3,
#  "coalesced": 2, "size": 3, "hit_rate": 0.8}
```
