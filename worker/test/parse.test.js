import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { test } from "node:test";

import {
  ParseError,
  extractSearchData,
  parseDetail,
  parseLatest,
  parseSearchPayload,
  parseTag,
  splitBiblio,
  validatePage,
  validateText,
} from "../src/parse.js";

const root = dirname(fileURLToPath(import.meta.url));
const fixtures = join(root, "..", "..", "tests", "fixtures");
const read = (name) => readFileSync(join(fixtures, name), "utf8");

test("parseLatest 解析最新图书列表", () => {
  const books = parseLatest(read("latest.html"));
  assert.equal(books.length, 20);
  const first = books[0];
  assert.equal(first.id, "38613720");
  assert.equal(first.name, "空地");
  assert.equal(first.auther, "李颖迪");
  assert.equal(first.publisher, "文汇出版社");
  assert.equal(first.price, "59.00");
  assert.equal(first.comment, "8.3");
  assert.equal(first.rating_count, "227");
  assert.match(first.url, /subject\/38613720\/$/);
});

test("parseTag 解析标签列表", () => {
  const books = parseTag(read("tag.html"));
  assert.equal(books.length, 20);
  assert.equal(books[0].id, "38370177");
  assert.match(books[0].info, /^马伯庸/);
  assert.equal(books[0].comment, "6.7");
  assert.equal(books[0].rating_count, "5015");
});

test("parseDetail 解析详情页", () => {
  const book = parseDetail(read("detail.html"));
  assert.equal(book.name, "三体");
  assert.equal(book.auther, "刘慈欣");
  assert.deepEqual(book.authors, ["刘慈欣"]);
  assert.equal(book.publisher, "重庆出版社");
  assert.equal(book.ISBN, "9787536692930");
  assert.equal(book.price, "23.00");
  assert.equal(book.score, "8.9");
  assert.equal(book.score_num, "519247");
  assert.equal(book.comment.star5, "62.6");
  assert.equal(Object.keys(book.comment).length, 5);
  assert.match(book.introduction, /红岸工程/);
  assert.match(book.auther_introduction, /刘慈欣，祖籍河南/);
});

test("parseDetail 对非详情页抛 ParseError", () => {
  assert.throws(() => parseDetail("<html><body>nope</body></html>"), ParseError);
});

test("parseTag 空列表抛 ParseError", () => {
  assert.throws(() => parseTag("<html><ul></ul></html>"), ParseError);
});

test("splitBiblio 兼容不同字段顺序", () => {
  const parsed = splitBiblio("李颖迪 / 2026-10 / 文汇出版社 / 59.00 / 平装");
  assert.equal(parsed.auther, "李颖迪");
  assert.equal(parsed.publish_date, "2026-10");
  assert.equal(parsed.publisher, "文汇出版社");
  assert.equal(parsed.price, "59.00");
  assert.equal(parsed.binding, "平装");
});

test("extractSearchData 解析明文 JSON（含字符串中的分号）", () => {
  const data = extractSearchData(read("search.html"));
  assert.equal(data.total, 250);
  const result = parseSearchPayload(data);
  assert.equal(result.books.length, 15);
  assert.equal(result.books[0].id, "2567698");
  assert.equal(result.books[0].rating, 8.9);
  assert.equal(result.series.length, 1);
});

test("extractSearchData 处理不完整数据", () => {
  assert.throws(() => extractSearchData("<html>nothing</html>"), ParseError);
  assert.throws(() => extractSearchData("window.__DATA__ = {"), ParseError);
});

test("参数校验", () => {
  assert.equal(validateText("  小说  ", "tag"), "小说");
  assert.throws(() => validateText("", "tag"), /不能为空/);
  assert.throws(() => validateText(null, "tag"), /缺少参数/);
  assert.equal(validatePage(null, { oneBased: false }), 0);
  assert.equal(validatePage("3"), 3);
  assert.throws(() => validatePage("0"), /小于等于 0/);
  assert.throws(() => validatePage("abc"), /整数/);
  assert.throws(() => validatePage("999"), /上限/);
});
