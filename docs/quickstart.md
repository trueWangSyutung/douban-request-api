# 快速开始

## 本地运行

需要 Python 3.10+。

```bash
git clone https://github.com/trueWangSyutung/douban-request-api.git
cd douban-request-api

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[server]"                          # 开发/生产依赖
python -m douban_api serve --port 5000
```

打开 <http://127.0.0.1:5000> 可以看到接口索引，<http://127.0.0.1:5000/docs> 是 Swagger UI。

也可以直接用兼容入口：

```bash
python api.py
```

## 第一个请求

=== "最新图书"

    ```bash
    curl -s "http://127.0.0.1:5000/api/v1/books/latest?type=全部&page=0"
    ```

=== "按标签"

    ```bash
    curl -s "http://127.0.0.1:5000/api/v1/books/tag?tag=小说&page=1"
    ```

=== "图书详情"

    ```bash
    curl -s "http://127.0.0.1:5000/api/v1/books/2567698"
    ```

=== "搜索"

    ```bash
    curl -s "http://127.0.0.1:5000/api/v1/search?q=三体"
    ```

返回示例（节选）：

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
      "rating": 8.9
    }
  ],
  "meta": { "cached": false, "elapsed_ms": 231.4, "ttl": 600, "version": "2.0.0" }
}
```

## Docker

```bash
docker build -t douban-api .
docker run --rm -p 8080:8080 douban-api
curl -s http://127.0.0.1:8080/healthz
```

或使用预构建镜像：

```bash
docker run --rm -p 8080:8080 ghcr.io/truewangSyutung/douban-request-api:latest
```

## 生产运行

```bash
gunicorn -c gunicorn.conf.py douban_api.app:create_app()
```

`gunicorn.conf.py` 默认使用 `gthread`（4 worker × 8 线程）——本服务几乎全部时间都在等上游
网络 IO，多线程比多进程更省内存，并发能力也更好。

## 配置项

所有配置都通过环境变量注入，默认值即可开箱使用。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `HOST` / `PORT` | `0.0.0.0` / `5000` | 监听地址 |
| `LOG_LEVEL` | `info` | 日志级别 |
| `UPSTREAM_BASE` | `https://book.douban.com` | 图书站地址（可指向镜像/代理） |
| `SEARCH_BASE` | `https://search.douban.com` | 搜索站地址 |
| `CONNECT_TIMEOUT` / `READ_TIMEOUT` | `3.5` / `7.0` | 上游超时（秒） |
| `HTTP_RETRIES` | `2` | 幂等 GET 重试次数 |
| `TTL_LATEST` / `TTL_TAG` / `TTL_DETAIL` / `TTL_SEARCH` | `300` / `600` / `1800` / `600` | 各类缓存 TTL（秒，0 = 关闭） |
| `CACHE_MAXSIZE` | `4096` | 内存缓存条目上限 |
| `REDIS_URL` | 空 | 配置后启用 L1 内存 + L2 Redis 两级缓存 |
| `RATE_LIMIT_RPM` | `120` | 单 IP 每分钟请求数，0 = 关闭限流 |
| `RATE_LIMIT_BURST` | 自动 | 令牌桶容量 |
| `GZIP_MIN_SIZE` | `512` | 超过该字节数才压缩 |
| `CORS_ORIGINS` | `*` | 允许的跨域来源 |
| `PUBLIC_CACHE` | `true` | 是否下发 `Cache-Control` |
| `TRUST_PROXY` | `false` | 在反向代理后启用 `X-Forwarded-For` |
| `WARMUP` | `false` | 启动时预热最新图书与「小说」标签 |

示例：

```bash
PORT=8080 RATE_LIMIT_RPM=60 TTL_TAG=900 WARMUP=true python -m douban_api serve
```

## 下一步

- [接口概览](api/index.md)：字段、错误码、缓存与限流细节
- [部署](deployment/index.md)：Pages / Worker / Docker
- [性能](performance.md)：优化点与基准数据
