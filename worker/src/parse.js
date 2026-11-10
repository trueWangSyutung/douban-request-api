/**
 * 豆瓣页面解析（Cloudflare Worker 版）。
 *
 * 与 Python 端 src/douban_api/parsers.py 保持相同的输出结构，
 * 这样文档、快照与边缘 API 的字段是一致的。
 * 用纯 JS 的 node-html-parser 而不是 HTMLRewriter：解析函数是同步纯函数，
 * 可以在 Node 里用真实 fixture 做单元测试。
 */
import { parse } from "node-html-parser";

const WS = /[\s\u3000\xa0]+/g;
const COUNT_RE = /(\d[\d,]*)\s*人(?:评价|评分)/;
const SUBJECT_RE = /\/subject\/(\d{4,12})/;
const YEAR_RE = /^((?:19|20)\d{2}(?:[-/.]\d{1,2}){0,2})$/;

export class ParseError extends Error {
  constructor(message = "上游响应解析失败") {
    super(message);
    this.name = "ParseError";
  }
}

const NAMED_ENTITIES = {
  nbsp: " ", amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", mdash: "—", ndash: "–",
  hellip: "…", middot: "·", ldquo: "“", rdquo: "”", lsquo: "‘", rsquo: "’",
};

/** node-html-parser 不会解码 `&nbsp;` 之类的命名实体，这里补齐。 */
export function decodeEntities(value) {
  if (!value.includes("&")) return value;
  return value.replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z]+);/g, (match, code) => {
    if (code[0] === "#") {
      const point = code[1] === "x" || code[1] === "X"
        ? Number.parseInt(code.slice(2), 16)
        : Number.parseInt(code.slice(1), 10);
      if (Number.isFinite(point) && point > 0 && point < 0x110000) {
        return String.fromCodePoint(point);
      }
      return match;
    }
    const named = NAMED_ENTITIES[code.toLowerCase()];
    return named === undefined ? match : named;
  });
}

export function clean(value) {
  if (!value) return "";
  return decodeEntities(String(value)).replace(WS, " ").trim();
}

export function subjectId(href) {
  const match = SUBJECT_RE.exec(href || "");
  return match ? match[1] : "";
}

/** "作者 / 出版社 / 2008-1 / 23.00元" → 结构化字段（顺序在不同页面并不固定）。 */
export function splitBiblio(raw) {
  const parts = String(raw || "")
    .split("/")
    .map((part) => clean(part))
    .filter(Boolean);
  const result = {
    info: clean(raw),
    auther: "",
    publisher: "",
    price: "",
    publish_date: "",
    binding: "",
  };
  if (!parts.length) return result;
  result.auther = parts[0];
  for (const part of parts.slice(1)) {
    if (!result.price && /^\d+(\.\d+)?\s*元?$/.test(part)) {
      result.price = part.replace(/\s*元$/, "");
      continue;
    }
    if (!result.publish_date && YEAR_RE.test(part)) {
      result.publish_date = part;
      continue;
    }
    if (!result.publisher && /出版|书局|印书馆|集团/.test(part)) {
      result.publisher = part;
      continue;
    }
    if (!result.binding && /^(平装|精装|Hardcover|Paperback|Kindle|电子书|盒装)$/.test(part)) {
      result.binding = part;
    }
  }
  if (!result.publisher && parts.length >= 3) {
    result.publisher = parts[2];
  }
  return result;
}

function textOf(node) {
  return clean(node ? node.textContent : "");
}

function ratingOf(node) {
  let score = "";
  let count = "";
  const scored = node.querySelectorAll(".rating_nums, .font-small");
  for (const span of scored) {
    const text = textOf(span);
    if (/^\d+(\.\d+)?$/.test(text)) {
      score = text;
      break;
    }
  }
  if (!score) {
    for (const span of node.querySelectorAll("span[class*='allstar']")) {
      const match = /allstar(\d{2})/.exec(span.getAttribute("class") || "");
      if (match) {
        score = (Number(match[1]) / 10).toFixed(1).replace(/\.0$/, "");
        break;
      }
    }
  }
  const match = COUNT_RE.exec(clean(node.textContent));
  if (match) count = match[1].replace(/,/g, "");
  return { score, count };
}

export function parseLatest(html) {
  const root = parse(html, { comment: false });
  const books = [];
  for (const node of root.querySelectorAll("li.media")) {
    const link =
      node.querySelector(".media__img a") || node.querySelector("a[href*='/subject/']");
    const id = subjectId(link && link.getAttribute("href"));
    if (!id) continue;
    const cover =
      node.querySelector("img.subject-cover") || node.querySelector("img");
    const info = textOf(node.querySelector("p.subject-abstract"));
    const biblio = splitBiblio(info);
    const rating = ratingOf(node);
    books.push({
      id,
      cover: cover ? cover.getAttribute("src") || "" : "",
      name: textOf(node.querySelector("h2 a")) || textOf(node.querySelector("h2")),
      ...biblio,
      comment: rating.score,
      rating_count: rating.count,
      url: `https://book.douban.com/subject/${id}/`,
    });
  }
  if (!books.length) throw new ParseError("未能在最新图书页解析到任何条目");
  return books;
}

export function parseTag(html) {
  const root = parse(html, { comment: false });
  const books = [];
  for (const node of root.querySelectorAll("li.subject-item")) {
    const link =
      node.querySelector("h2 a") || node.querySelector("a.nbg");
    const id = subjectId(link && link.getAttribute("href"));
    if (!id) continue;
    const cover = node.querySelector("img");
    const rating = ratingOf(node);
    books.push({
      id,
      cover: cover ? cover.getAttribute("src") || "" : "",
      name: textOf(node.querySelector("h2 a")) || textOf(node.querySelector("h2")),
      info: textOf(node.querySelector(".pub")),
      comment: rating.score,
      rating_count: rating.count,
      url: `https://book.douban.com/subject/${id}/`,
    });
  }
  if (!books.length) throw new ParseError("未能在标签页解析到任何条目");
  return books;
}

/** 按 <br> 与 span.pl 切行，再解析 "标签: 值"。 */
function infoLines(infoNode) {
  const html = infoNode.innerHTML
    .replace(/<br\s*\/?>/gi, "\u0000")
    .replace(/<[^>]+>/g, " ");
  return html
    .split("\u0000")
    .map((line) => clean(line))
    .filter(Boolean);
}

function parseIntro(node) {
  if (!node) return "";
  const paragraphs = node
    .querySelectorAll("p")
    .map((p) => clean(p.textContent))
    .filter(Boolean);
  if (paragraphs.length) return paragraphs.join("\n");
  return clean(node.textContent).replace(/\(?展开全部\)?$/, "").trim();
}

export function parseDetail(html) {
  const root = parse(html, { comment: false });
  const titleNode =
    root.querySelector("h1 span[property='v:itemreviewed']") || root.querySelector("h1 span");
  const name = textOf(titleNode);
  if (!name) throw new ParseError("未能在详情页解析到书名，页面结构可能已变更");

  const cover = root.querySelector("#mainpic img") || root.querySelector(".article img");

  const info = {};
  const authors = [];
  const infoNode = root.querySelector("#info");
  if (infoNode) {
    for (const line of infoLines(infoNode)) {
      const match = /^([^:：]{1,12})\s*[:：]\s*(.*)$/.exec(line);
      if (!match) continue;
      const label = clean(match[1]).replace(/[:：]$/, "");
      const value = clean(match[2]);
      if (!value) continue;
      if (label === "作者") authors.push(value);
      else if (!(label in info)) info[label] = value;
    }
    if (authors.length) info["作者"] = authors.join(" / ");
  }

  const score = textOf(root.querySelector("strong[property='v:average']"));
  const votes = textOf(root.querySelector("span[property='v:votes']"));
  const comment = {};
  root.querySelectorAll("span.rating_per").forEach((node, index) => {
    if (index < 5) comment[`star${5 - index}`] = clean(node.textContent).replace("%", "");
  });
  for (let star = 1; star <= 5; star += 1) {
    const key = `star${star}`;
    if (!(key in comment)) comment[key] = "0";
  }

  let authorIntro = "";
  for (const heading of root.querySelectorAll("h2")) {
    if (!textOf(heading).includes("作者简介")) continue;
    let sibling = heading.nextElementSibling;
    while (sibling) {
      const intro = sibling.querySelector(".intro");
      if (intro) {
        authorIntro = parseIntro(intro);
        break;
      }
      sibling = sibling.nextElementSibling;
    }
    if (authorIntro) break;
  }
  if (!authorIntro) {
    const intros = root.querySelectorAll(".intro");
    if (intros.length > 1) authorIntro = parseIntro(intros[1]);
  }

  const intro = parseIntro(
    root.querySelector("#link-report .intro") || root.querySelector("#link-report")
  );
  const tags = root
    .querySelectorAll("#db-tags-section a, .tags a")
    .map((node) => textOf(node))
    .filter(Boolean);

  return {
    name,
    cover: cover ? cover.getAttribute("src") || "" : "",
    auther: info["作者"] || "",
    authors,
    publisher: info["出版社"] || "",
    producer: info["出品方"] || "",
    publish_date: info["出版年"] || "",
    pages: info["页数"] || "",
    binding: info["装帧"] || "",
    price: clean((info["定价"] || "").replace(/元$/, "")),
    ISBN: info["ISBN"] || "",
    subtitle: info["副标题"] || "",
    original_title: info["原作名"] || "",
    translator: info["译者"] || "",
    series: info["丛书"] || "",
    score: score || "0",
    score_num: votes || "0",
    comment,
    introduction: intro,
    auther_introduction: authorIntro,
    tags,
    info,
  };
}

/** 从搜索页里取出 window.__DATA__（当前豆瓣直接返回明文 JSON）。 */
export function extractSearchData(html) {
  const marker = /window\.__DATA__\s*=\s*/.exec(html);
  if (!marker) throw new ParseError("搜索页中未找到 window.__DATA__");
  const rest = html.slice(marker.index + marker[0].length);
  const trimmed = rest.replace(/^\s+/, "");
  const start = trimmed.search(/[{\["]/);
  if (start < 0) throw new ParseError("搜索数据结构无法识别");
  const body = trimmed.slice(start);
  const end = scanJsonEnd(body);
  if (end < 0) throw new ParseError("搜索数据不完整");
  let value;
  try {
    value = JSON.parse(body.slice(0, end));
  } catch (err) {
    throw new ParseError("搜索数据不是合法 JSON（可能是旧版加密格式）");
  }
  if (typeof value === "string") {
    throw new ParseError("上游返回旧版加密搜索数据，Worker 暂不支持，请使用 Flask 服务");
  }
  if (!value || typeof value !== "object") throw new ParseError("搜索数据结构异常");
  return value;
}

/** 扫描到第一个完整的 JSON 值结束位置（正确处理字符串与转义）。 */
function scanJsonEnd(text) {
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') inString = true;
    else if (ch === "{" || ch === "[") depth += 1;
    else if (ch === "}" || ch === "]") {
      depth -= 1;
      if (depth === 0) return i + 1;
    }
  }
  return -1;
}

export function parseSearchPayload(payload) {
  let data = payload;
  if (!Array.isArray(data.items) && data.payload && typeof data.payload === "object") {
    data = data.payload;
  }
  const books = [];
  const series = [];
  let author = null;
  for (const item of data.items || []) {
    if (!item || typeof item !== "object") continue;
    const tpl = item.tpl_name || "";
    const rating = item.rating || {};
    if (tpl === "search_subject" || tpl === "book") {
      books.push({
        id: String(item.id || subjectId(item.url || "")),
        name: clean(item.title),
        cover: item.cover_url || "",
        info: clean(item.abstract),
        comment_count: rating.count ?? null,
        rating: rating.value ?? null,
        url: item.url || "",
      });
    } else if (tpl === "search_common" || tpl === "search_author") {
      author = {
        id: item.id,
        name: clean(item.title),
        info: clean(item.abstract_2 || item.abstract),
        img: item.cover_url || "",
        url: item.url || "",
      };
    } else if (tpl === "search_simple" || tpl === "search_series") {
      series.push({
        id: item.id,
        name: clean(item.title),
        info: clean(item.abstract),
        url: item.url || "",
      });
    }
  }
  const result = {
    books,
    total: data.total ?? books.length,
    q: clean(data.text) || null,
  };
  if (author) result.author = author;
  if (series.length) result.series = series;
  return result;
}

/** 参数校验（与 Python 端规则一致），失败抛 ParseError 之外由调用方处理。 */
export function validateText(value, name, { maxLen = 64, required = true } = {}) {
  if (value === null || value === undefined) {
    if (required) throw Object.assign(new Error(`缺少参数 ${name}`), { code: 10020 });
    return "";
  }
  const text = String(value).trim();
  if (!text) throw Object.assign(new Error(`参数 ${name} 不能为空`), { code: 10021 });
  if (text.length > maxLen) throw Object.assign(new Error(`参数 ${name} 过长`), { code: 10020 });
  if (/[\u0000-\u001f]/.test(text)) throw Object.assign(new Error(`参数 ${name} 含非法字符`), { code: 10020 });
  return text;
}

export function validatePage(value, { oneBased = true, max = 50 } = {}) {
  const minimum = oneBased ? 1 : 0;
  if (value === null || value === undefined || value === "") return oneBased ? 1 : 0;
  const page = Number(value);
  if (!Number.isInteger(page)) throw Object.assign(new Error("page 必须是整数"), { code: 10020 });
  if (page < minimum) throw Object.assign(new Error("页数不能小于等于 0"), { code: 10022 });
  if (page > max) throw Object.assign(new Error(`page 超出上限（${max}）`), { code: 10020 });
  return page;
}
