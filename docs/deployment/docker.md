# Docker / 自建服务器

## 镜像

推送到 `master` 或打 `v*` tag 后，`docker.yml` 会构建多架构镜像并推送到 GHCR：

```bash
docker pull ghcr.io/truewangSyutung/douban-request-api:latest
docker run -d --name douban-api -p 8080:8080 ghcr.io/truewangSyutung/douban-request-api:latest
```

镜像基于 `python:3.12-slim`，非 root 用户运行，内置 healthcheck，约 120MB。

## docker compose

```bash
docker compose up -d --build
curl -s http://127.0.0.1:8080/healthz
```

需要 Redis 共享缓存时：

```yaml
services:
  api:
    image: ghcr.io/truewangSyutung/douban-request-api:latest
    environment:
      REDIS_URL: redis://redis:6379/0
      WEB_CONCURRENCY: "4"
      GUNICORN_THREADS: "8"
    ports: ["8080:8080"]
  redis:
    image: redis:7-alpine
```

## 传统服务器（含宝塔）

```bash
git clone https://github.com/trueWangSyutung/douban-request-api.git
cd douban-request-api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[server,legacy]"
gunicorn -c gunicorn.conf.py douban_api.app:create_app()
```

用 systemd 托管：

```ini
# /etc/systemd/system/douban-api.service
[Unit]
Description=douban-request-api
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/douban-request-api
Environment=PORT=5000
Environment=WARMUP=true
ExecStart=/opt/douban-request-api/.venv/bin/gunicorn -c gunicorn.conf.py douban_api.app:create_app()
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload && systemctl enable --now douban-api
```

### Nginx 反代

```nginx
server {
    listen 443 ssl http2;
    server_name douban.example.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }
}
```

启用 `TRUST_PROXY=true`，限流才会按真实客户端 IP 计数。

## 容量估算

服务几乎全部时间在等上游（约 230ms/次，命中缓存 <1ms），瓶颈是线程数而不是 CPU：

| 配置 | 并发（估算） | 说明 |
| --- | --- | --- |
| 2 worker × 8 线程 | ~16 个上游请求 | 256MB 内存足够 |
| 4 worker × 8 线程 | ~32 | 推荐，配合 Redis |
| Cloudflare Worker | 平台自动扩缩 | 首选，零运维 |

## 健康检查

```bash
curl -sf http://127.0.0.1:8080/healthz || exit 1
curl -s http://127.0.0.1:8080/metrics | jq '.cache.hit_rate'
```

## 升级

```bash
docker compose pull && docker compose up -d
```

数据全部来自豆瓣，没有本地数据库，升级无需迁移。
