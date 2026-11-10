# 性能

所有数字都可以用 `python -m benchmarks.bench --iterations 12 --live` 复现
（同一台机器、同一个网络）。结果同时保存在 [`benchmarks/results.md`](https://github.com/trueWangSyutung/douban-request-api/blob/master/benchmarks/results.md)。

## 结论

| 场景 | v1 | v2 | 变化 |
| --- | ---: | ---: | ---: |
| 最新图书（真实豆瓣，冷请求） | **1017 ms** | **231 ms** | 4.4× 更快 |
| 列表页解析（同一份 HTML） | 485 ms | 3.2 ms | **151×** |
| 搜索数据解码 | 62 ms | 0.10 ms | **645×** |
| 缓存命中（服务层） | 无缓存 | **~10 µs** | — |
| API 端到端（含 Flask，命中缓存） | — | 0.30 ms | — |
| 响应体积（最新图书 JSON） | 8.8 KB | 2.1 KB | −76%（gzip） |

> 旧实现还**无法解析**当前的标签页与详情页（`IndexError`），也就是说 v1 实际上已经坏掉了；
> 这不只是快慢问题。

## 优化点

### 1. 连接复用（收益最大）

```python
# v1：每个请求新建 TCP + TLS
requests.get(url, headers=headers)

# v2：进程级 Session + 连接池 + 幂等重试
session = requests.Session()
session.mount("https://", HTTPAdapter(pool_connections=32, pool_maxsize=32, max_retries=...))
```

TLS 握手通常 100–200ms，冷请求里这一项占主导。基准里用本机 keep-alive 服务测得的
1.6× 只是下限（无网络 RTT）；真实跨境访问时收益更大。

### 2. 解析从"整页正则"改为 lxml XPath

- 旧代码在 100KB HTML 上反复 `re.findall`，且 `<p class="...">(.*?)/(.*?)/(.*?)/(.*?)/(.*?)</p>`
  有 5 个惰性分组，单条列表项就要几十毫秒；在整页上甚至会发生灾难性回溯。
- 新代码一次 `html.fromstring` + 结构化 XPath，附带字段语义（`split_biblio` 按特征而不是
  固定下标识别作者/出版社/年份/价格），对豆瓣改版更稳。

### 3. 去掉 PyExecJS

旧版搜索要 `execjs.compile(60KB JS)` 并在**每次请求 fork 一个 Node 进程**（~62ms、40MB）。
现在豆瓣的 `window.__DATA__` 已是明文 JSON，直接 `json.loads`（~0.1ms）；
只有上游回退到旧格式时才走内置 quickjs（~16ms，不 fork 进程）。

### 4. TTL + LRU 缓存与单飞

- 列表 5 分钟、标签 10 分钟、详情 30 分钟、搜索 10 分钟；
- 同一 key 并发只回源一次（single-flight），避免缓存击穿；
- 上游抖动时返回上一份过期数据（stale-while-error）；
- 可选 `REDIS_URL`：L1 进程内 + L2 Redis，多 worker/多副本共享。

### 5. gzip + ETag/304 + Cache-Control

JSON 压缩到原来的 24%，压缩耗时 0.1ms；`ETag` 只基于业务数据（不含 `meta`），
客户端带 `If-None-Match` 时返回 304、零正文。

### 6. 限制资源浪费

- 参数在打上游之前校验（非法 id/超长 q/越界 page 直接 400）；
- 单 IP 令牌桶限流（默认 120 rpm），429 带 `Retry-After`；
- 上游超时 3.5s/7s + 2 次退避重试，只重试幂等 GET。

## 复现

```bash
pip install -e ".[dev,legacy,server]"
python -m benchmarks.bench --iterations 12 --live
```

输出 `benchmarks/results.md` 与 `benchmarks/results.json`。

## 注意

- 延迟受本机网络与豆瓣限流影响，数字会波动；表格取自一次完整运行。
- 缓存让"重复查询"几乎免费，但**不要**借此高频遍历豆瓣。
- Cloudflare Worker 版本的解析函数相同，边缘命中缓存时约 1ms（实测 `X-Cache: HIT`）。
