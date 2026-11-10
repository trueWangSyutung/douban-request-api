# Cloudflare Worker（实时 API）

`worker/` 是同一套接口的 Worker 实现：用 `node-html-parser` 解析、Cloudflare Cache API 做边缘
缓存，路由、字段与错误码和 Flask 版本一致。已用 `wrangler dev` 在本机对真实豆瓣验证通过。

## 能力对比

| 能力 | Flask/Docker | Worker |
| --- | --- | --- |
| 实时抓取 | ✅ | ✅ |
| 边缘缓存 | 需 Redis/CDN | ✅ `caches.default` |
| 冷启动 | 容器启动 | 0ms |
| 运维 | 需服务器 | 无 |
| Redis 共享缓存 | ✅ | 不适用（用边缘缓存 + KV 可选） |
| 旧版加密搜索数据 | ✅ quickjs 回退 | ❌ 返回 10060 提示 |

## 一键部署（GitHub Actions）

1. 在 Cloudflare 控制台创建 API Token：**My Profile → API Tokens → Create Token**，
   模板选 *Edit Cloudflare Workers*（或自定义 `Workers Scripts:Edit` + `Account:Read`）。
2. 在 GitHub 仓库 **Settings → Secrets and variables → Actions** 添加：
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`（Workers 概览页右下角可复制）
3. 在 **Variables** 里添加 `ENABLE_WORKER_DEPLOY = true`。
4. push 到 `master` 修改 `worker/**`，或手动运行 `worker` workflow。

部署成功后 Actions 日志里会打印 `https://douban-request-api.<子域>.workers.dev`。

> 没有配置 Secret 时 `worker.yml` 只跑测试与打包校验（`deploy --dry-run`），
> 不会失败，也不会部署。

## 本地开发

```bash
cd worker
npm install
npm test                 # 用真实 HTML fixture 做单元测试
npx wrangler dev         # 默认 http://127.0.0.1:8787
```

```bash
curl -s "http://127.0.0.1:8787/api/v1/search?q=三体" | head -c 200
curl -s "http://127.0.0.1:8787/api/v1/books/2567698" | jq '.book.score'
```

## 手动部署

```bash
cd worker
npx wrangler login
npx wrangler deploy
```

## 自定义域名

```toml
# worker/wrangler.toml
routes = [
  { pattern = "douban.example.com/*", zone_name = "example.com" }
]
```

或者在 Cloudflare 控制台 Workers → Settings → Triggers 里添加 Custom Domain。

## 缓存策略

| 接口 | 边缘 TTL | 说明 |
| --- | ---: | --- |
| `/api/v1/books/latest` | 300s | 与 Flask 端一致 |
| `/api/v1/books/tag` | 600s | |
| `/api/v1/books/{id}` | 1800s | |
| `/api/v1/search` | 600s | |

命中缓存时响应头是 `X-Cache: HIT`。缓存 key 是归一化后的 URL，与调用方的查询顺序无关。

## 注意事项

- Cloudflare 出口 IP 属于机房网段，豆瓣**可能**对部分请求返回 403/429。遇到这种情况：
  降低请求频率、换用自建服务，或给 `fetch` 增加代理层（把 `UPSTREAM_BASE` 指向你的反代）。
- 免费额度：10 万次请求/天；Worker 单次 CPU 10ms 限制对纯 IO 型任务足够。
- Worker 不支持 `eval`，所以没有打包旧版 JS 解密逻辑；当前豆瓣已返回明文 JSON，
  不影响正常使用。
