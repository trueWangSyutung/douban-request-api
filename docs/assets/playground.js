/* 文档站内的 API 演练场：支持「本站静态快照」与「在线 API」两种模式。 */
(function () {
  "use strict";

  var SNAPSHOT_BASE = "../api/v1";
  var STORE_KEY = "douban-api-playground-base";

  var $ = function (id) { return document.getElementById(id); };
  var statusEl = $("pg-status");
  var outputEl = $("pg-output");
  var baseInput = $("pg-base");
  var endpointEl = $("pg-endpoint");
  var aEl = $("pg-a");
  var bEl = $("pg-b");

  var fields = {
    latest: { a: "type=全部", b: "page=0", hint: "分类可选，页码从 0 开始" },
    tag: { a: "tag=小说", b: "page=1", hint: "标签名，页码从 1 开始" },
    detail: { a: "id=2567698", b: null, hint: "豆瓣图书 ID" },
    search: { a: "q=三体", b: null, hint: "关键词" }
  };

  function mode() {
    var checked = document.querySelector('input[name="pg-mode"]:checked');
    return checked ? checked.value : "static";
  }

  function parsePair(value) {
    var idx = value.indexOf("=");
    if (idx < 0) return [value.trim(), ""];
    return [value.slice(0, idx).trim(), value.slice(idx + 1).trim()];
  }

  function currentParams() {
    var params = {};
    var a = parsePair(aEl.value || "");
    if (a[0]) params[a[0]] = a[1];
    if (bEl.value) {
      var b = parsePair(bEl.value);
      if (b[0]) params[b[0]] = b[1];
    }
    return params;
  }

  function setStatus(text, cls) {
    statusEl.textContent = text;
    statusEl.className = "pg-status" + (cls ? " " + cls : "");
  }

  function render(payload) {
    var text = JSON.stringify(payload, null, 2);
    if (text.length > 40000) {
      text = text.slice(0, 40000) + "\n… (已截断)";
    }
    outputEl.textContent = text;
  }

  function humanSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1024 / 1024).toFixed(2) + " MB";
  }

  async function timedFetch(url, headers) {
    var started = performance.now();
    var response = await fetch(url, { headers: headers || {} });
    var buffer = await response.arrayBuffer();
    var elapsed = Math.round(performance.now() - started);
    var text = new TextDecoder("utf-8").decode(buffer);
    var data;
    try {
      data = JSON.parse(text);
    } catch (err) {
      data = { raw: text.slice(0, 2000) };
    }
    return { response: response, data: data, elapsed: elapsed, bytes: buffer.byteLength };
  }

  function liveBase() {
    var base = (baseInput.value || "").trim().replace(/\/+$/, "");
    return base;
  }

  function staticSearch(index, query) {
    var q = query.trim().toLowerCase();
    var books = (index.books || []).filter(function (book) {
      var haystack = [book.name, book.info, book.auther].join(" ").toLowerCase();
      return haystack.indexOf(q) >= 0;
    });
    return {
      code: 200,
      msg: "success (静态快照：浏览器端过滤)",
      q: query,
      total: books.length,
      snapshot_count: index.count,
      generated_at: index.generated_at,
      books: books
    };
  }

  async function send() {
    var params = currentParams();
    var endpoint = endpointEl.value;
    var useLive = mode() === "live";
    setStatus("请求中…", "busy");

    try {
      var result;
      if (!useLive) {
        if (endpoint === "latest") {
          result = await timedFetch(SNAPSHOT_BASE + "/books/latest.json");
        } else if (endpoint === "tag") {
          var tag = params.tag || "小说";
          result = await timedFetch(SNAPSHOT_BASE + "/books/tag/" + encodeURIComponent(tag) + ".json");
        } else if (endpoint === "detail") {
          var id = params.id || "2567698";
          result = await timedFetch(SNAPSHOT_BASE + "/books/" + encodeURIComponent(id) + ".json");
        } else {
          var indexResult = await timedFetch(SNAPSHOT_BASE + "/search/index.json");
          result = indexResult;
          result.data = staticSearch(indexResult.data, params.q || "");
          result.response = { ok: true, status: 200, headers: new Headers() };
        }
      } else {
        var base = liveBase();
        if (!base) {
          setStatus("请先填写在线 API 地址", "error");
          return;
        }
        var url;
        if (endpoint === "latest") {
          url = base + "/api/v1/books/latest?type=" + encodeURIComponent(params.type || "全部") +
                "&page=" + encodeURIComponent(params.page || "0");
        } else if (endpoint === "tag") {
          url = base + "/api/v1/books/tag?tag=" + encodeURIComponent(params.tag || "小说") +
                "&page=" + encodeURIComponent(params.page || "1");
        } else if (endpoint === "detail") {
          url = base + "/api/v1/books/" + encodeURIComponent(params.id || "2567698");
        } else {
          url = base + "/api/v1/search?q=" + encodeURIComponent(params.q || "三体");
        }
        result = await timedFetch(url, { Accept: "application/json" });
      }

      if (!result.response.ok) {
        setStatus("HTTP " + result.response.status + " · " + result.elapsed + " ms", "error");
      } else {
        var cache = result.response.headers.get("X-Cache");
        setStatus(
          "HTTP " + result.response.status + " · " + result.elapsed + " ms · " +
          humanSize(result.bytes) + (cache ? " · cache " + cache : " · 静态文件"),
          "ok"
        );
      }
      render(result.data);
    } catch (err) {
      setStatus("请求失败：" + (err && err.message ? err.message : err), "error");
      outputEl.textContent = String(err);
    }
  }

  function syncFields() {
    var config = fields[endpointEl.value];
    aEl.placeholder = config.a || "";
    if (config.b) {
      bEl.placeholder = config.b;
      bEl.disabled = false;
      bEl.style.display = "";
    } else {
      bEl.value = "";
      bEl.disabled = true;
      bEl.style.display = "none";
    }
    if (!aEl.value || Object.keys(fields).some(function (key) {
      return aEl.value === fields[key].a;
    })) {
      aEl.value = config.a || "";
    }
    setStatus(config.hint || "就绪");
  }

  function syncMode() {
    var isLive = mode() === "live";
    baseInput.disabled = !isLive;
    baseInput.style.opacity = isLive ? "1" : ".5";
    if (isLive && !baseInput.value) {
      baseInput.value = localStorage.getItem(STORE_KEY) || "https://bookapi.oaixiv.org";
    }
  }

  document.querySelectorAll('input[name="pg-mode"]').forEach(function (input) {
    input.addEventListener("change", syncMode);
  });
  endpointEl.addEventListener("change", syncFields);
  $("pg-send").addEventListener("click", send);
  baseInput.addEventListener("change", function () {
    localStorage.setItem(STORE_KEY, baseInput.value.trim());
  });
  [aEl, bEl].forEach(function (input) {
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter") send();
    });
  });

  syncMode();
  syncFields();
})();
