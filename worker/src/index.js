/**
 * 豆瓣图书查询 API —— Cloudflare Worker 实现。
 *
 * 与 Flask 版本保持相同的路由、字段与错误码，并额外利用边缘能力：
 *  - Cache API 做边缘缓存（TTL 与 Python 端一致）
 *  - 自动 gzip/brotli（Cloudflare 对 JSON 自动压缩）
 *  - 全球 Anycast，无冷启动
 *
 * 部署：wrangler deploy（或 .github/workflows/worker.yml）
 */
import {
  ParseError,
  extractSearchData,
  parseDetail,
  parseLatest,
  parseSearchPayload,
  parseTag,
  validatePage,
  validateText,
} from "./parse.js";

const VERSION = "2.0.0";
const UPSTREAM_BASE = "https://book.douban.com";
const SEARCH_BASE = "https://search.douban.com";
const DOCS_URL = "https://trueWangSyutung.github.io/douban-request-api/";
const USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

const TTL = { latest: 300, tag: 600, detail: 1800, search: 600 };

const ERROR_CODES = {
  10020: "参数错误或缺失",
  10021: "参数为空",
  10022: "页数不能小于等于 0",
  10030: "上游（豆瓣）请求失败或超时",
  10040: "目标内容不存在",
  10050: "请求过于频繁，请稍后重试",
  10060: "上游响应解析失败",
  10070: "服务内部错误",
};

class ApiError extends Error {
  constructor(code, message, status) {
    super(message || ERROR_CODES[code] || "服务内部错误");
    this.name = "ApiError";
    this.code = code;
    this.status = status || 500;
  }
}

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,OPTIONS",
  "Access-Control-Expose-Headers": "X-Cache, X-Response-Time, ETag",
  "Access-Control-Allow-Headers": "Content-Type",
};

function jsonResponse(payload, { status = 200, ttl = 0, cached = null, started = 0 } = {}) {
  const headers = new Headers(CORS);
  headers.set("Content-Type", "application/json; charset=utf-8");
  headers.set("X-Response-Time", `${(performance.now() - started).toFixed(1)}ms`);
  headers.set("X-Content-Type-Options", "nosniff");
  if (ttl > 0) {
    headers.set("Cache-Control", `public, max-age=${Math.max(1, Math.floor(ttl / 2))}, stale-while-revalidate=${ttl}`);
  } else {
    headers.set("Cache-Control", "no-store");
  }
  if (cached !== null) headers.set("X-Cache", cached ? "HIT" : "MISS");
  return new Response(JSON.stringify(payload), { status, headers });
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** 豆瓣对机房 IP 偶发 403/429，带一个随机 bid cookie 重试通常可以恢复。 */
function randomBid() {
  const alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  let out = "";
  for (let i = 0; i < 11; i += 1) {
    out += alphabet[Math.floor(Math.random() * alphabet.length)];
  }
  return out;
}

async function fetchUpstream(url, attempt = 0) {
  const headers = {
    "User-Agent": USER_AGENT,
    Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    Referer: `${UPSTREAM_BASE}/`,
  };
  if (attempt > 0) headers.Cookie = `bid=${randomBid()}`;

  const response = await fetch(url, {
    headers,
    redirect: "follow",
    signal: AbortSignal.timeout(10000),
  }).catch(async (err) => {
    if (attempt < 2) {
      await sleep(250 * (attempt + 1));
      return null;
    }
    throw new ApiError(10030, `上游请求失败：${err.message}`, 502);
  });

  if (response === null) return fetchUpstream(url, attempt + 1);
  if (response.status === 404) throw new ApiError(10040, "目标内容不存在", 404);
  if ((response.status === 403 || response.status === 429 || response.status >= 500) && attempt < 2) {
    await sleep(250 * (attempt + 1));
    return fetchUpstream(url, attempt + 1);
  }
  if (response.status >= 400) {
    throw new ApiError(10030, `上游拒绝请求（${response.status}），可能触发风控`, 502);
  }
  return response.text();
}

async function cached(ctx, cacheUrl, ttl, producer) {
  const cache = caches.default;
  const key = new Request(cacheUrl, { method: "GET" });
  const hit = await cache.match(key);
  if (hit) {
    return { data: await hit.json(), cached: true };
  }
  const data = await producer();
  const stored = new Response(JSON.stringify(data), {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": `public, max-age=${ttl}`,
    },
  });
  ctx.waitUntil(cache.put(key, stored).catch(() => {}));
  return { data, cached: false };
}

function meta(data, cachedFlag, ttl, started) {
  return {
    ...data,
    meta: {
      cached: cachedFlag,
      elapsed_ms: Number((performance.now() - started).toFixed(2)),
      ttl,
      version: VERSION,
      runtime: "cloudflare-worker",
    },
  };
}

const LANDING = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>豆瓣图书查询 API v${VERSION}</title>
<style>body{font:16px/1.7 -apple-system,"PingFang SC",sans-serif;max-width:720px;margin:8vh auto;padding:0 20px}
code{background:rgba(127,127,127,.15);padding:1px 5px;border-radius:4px}a{color:#0a7d4f}</style>
</head><body><h1>豆瓣图书查询 API <small>v${VERSION} · Worker</small></h1>
<p>接口文档：<a href="${DOCS_URL}">${DOCS_URL}</a></p>
<ul>
<li><code>/api/v1/books/latest?type=全部&amp;page=0</code></li>
<li><code>/api/v1/books/tag?tag=小说&amp;page=1</code></li>
<li><code>/api/v1/books/2567698</code></li>
<li><code>/api/v1/search?q=三体</code></li>
<li><code>/healthz</code></li>
</ul>
<p style="opacity:.6;font-size:13px">数据来自豆瓣，仅供学习研究。</p></body></html>`;

function route(pathname) {
  const path = pathname.replace(/\/+$/, "") || "/";
  return path;
}

async function handle(request, env, ctx) {
  const started = performance.now();
  const url = new URL(request.url);
  const path = route(url.pathname);

  if (path === "/") {
    if (url.searchParams.get("format") === "json") {
      return jsonResponse(
        {
          name: "豆瓣图书查询 API",
          version: VERSION,
          runtime: "cloudflare-worker",
          docs: DOCS_URL,
          endpoints: [
            "/api/v1/books/latest",
            "/api/v1/books/tag",
            "/api/v1/books/{id}",
            "/api/v1/search",
            "/healthz",
          ],
        },
        { started }
      );
    }
    return new Response(LANDING, {
      headers: { "Content-Type": "text/html; charset=utf-8", ...CORS },
    });
  }

  if (path === "/healthz") {
    return jsonResponse(
      { status: "ok", version: VERSION, runtime: "cloudflare-worker", cache: "edge" },
      { started }
    );
  }

  if (path === "/openapi.json") {
    return jsonResponse(
      { openapi: "3.1.0", url: `${DOCS_URL}openapi.json`, note: "完整规范由文档站托管" },
      { started }
    );
  }

  if (path === "/api/v1/books/latest" || path === "/getNewBook") {
    const type = url.searchParams.get("type") || "全部";
    const subcat = type ? validateText(type, "type", { maxLen: 32 }) : "全部";
    const page = validatePage(url.searchParams.get("page"), { oneBased: false });
    const upstream = `${UPSTREAM_BASE}/latest?subcat=${encodeURIComponent(subcat)}&p=${page}`;
    const result = await cached(
      ctx,
      `https://cache.douban-api.internal/latest?subcat=${encodeURIComponent(subcat)}&p=${page}`,
      TTL.latest,
      async () => {
        const books = parseLatest(await fetchUpstream(upstream));
        return { code: 200, type: subcat, page, books };
      }
    );
    return jsonResponse(meta(result.data, result.cached, TTL.latest, started), {
      ttl: TTL.latest,
      cached: result.cached,
      started,
    });
  }

  if (path === "/api/v1/books/tag" || path === "/getType") {
    const tag = validateText(url.searchParams.get("tag"), "tag", { maxLen: 32 });
    const page = validatePage(url.searchParams.get("page"), { oneBased: true });
    const start = (page - 1) * 20;
    const upstream = `${UPSTREAM_BASE}/tag/${encodeURIComponent(tag)}?start=${start}&type=T`;
    const result = await cached(
      ctx,
      `https://cache.douban-api.internal/tag?tag=${encodeURIComponent(tag)}&page=${page}`,
      TTL.tag,
      async () => {
        const books = parseTag(await fetchUpstream(upstream));
        return { code: 200, tag, page, start, books };
      }
    );
    return jsonResponse(meta(result.data, result.cached, TTL.tag, started), {
      ttl: TTL.tag,
      cached: result.cached,
      started,
    });
  }

  const detailMatch = /^\/api\/v1\/books\/([^/]+)$/.exec(path);
  if (detailMatch || path === "/getBookDetail") {
    const raw = detailMatch ? decodeURIComponent(detailMatch[1]) : url.searchParams.get("id");
    if (raw === null || raw === undefined) throw new ApiError(10020, "缺少参数 id", 400);
    const subjectId = String(raw).trim();
    if (!subjectId) throw new ApiError(10021, "参数 id 不能为空", 400);
    if (!/^\d{4,12}$/.test(subjectId)) throw new ApiError(10020, "id 必须是 4-12 位数字的图书 ID", 400);
    const upstream = `${UPSTREAM_BASE}/subject/${subjectId}/`;
    let result;
    try {
      result = await cached(
        ctx,
        `https://cache.douban-api.internal/detail?id=${subjectId}`,
        TTL.detail,
        async () => {
          const book = parseDetail(await fetchUpstream(upstream));
          return { code: 200, book: { ...book, id: subjectId, url: upstream } };
        }
      );
    } catch (err) {
      if (err instanceof ApiError && err.code === 10040) {
        throw new ApiError(10040, `图书 ${subjectId} 不存在`, 404);
      }
      throw err;
    }
    return jsonResponse(meta(result.data, result.cached, TTL.detail, started), {
      ttl: TTL.detail,
      cached: result.cached,
      started,
    });
  }

  if (path === "/api/v1/search" || path === "/search") {
    const q = validateText(url.searchParams.get("q"), "q", { maxLen: 64 });
    const upstream = `${SEARCH_BASE}/book/subject_search?search_text=${encodeURIComponent(q)}`;
    const result = await cached(
      ctx,
      `https://cache.douban-api.internal/search?q=${encodeURIComponent(q)}`,
      TTL.search,
      async () => {
        const payload = extractSearchData(await fetchUpstream(upstream));
        const data = parseSearchPayload(payload);
        return { code: 200, msg: "success", ...data, q: data.q || q };
      }
    );
    return jsonResponse(meta(result.data, result.cached, TTL.search, started), {
      ttl: TTL.search,
      cached: result.cached,
      started,
    });
  }

  throw new ApiError(10040, `未知接口：${path}`, 404);
}

export default {
  async fetch(request, env, ctx) {
    const started = performance.now();
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS });
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return jsonResponse({ code: 10020, msg: "只支持 GET 请求" }, { status: 405, started });
    }
    try {
      const response = await handle(request, env, ctx);
      if (request.method === "HEAD") {
        return new Response(null, { status: response.status, headers: response.headers });
      }
      return response;
    } catch (err) {
      if (err instanceof ParseError) {
        return jsonResponse({ code: 10060, msg: err.message }, { status: 502, started });
      }
      if (err instanceof ApiError) {
        return jsonResponse({ code: err.code, msg: err.message }, { status: err.status, started });
      }
      if (typeof err.code === "number") {
        return jsonResponse({ code: err.code, msg: err.message }, { status: 400, started });
      }
      console.error("unexpected error", err);
      return jsonResponse({ code: 10070, msg: "服务内部错误" }, { status: 500, started });
    }
  },
};
