# 在线体验

下面这个页面可以直接调用接口，默认访问**实时 API**（<https://bookapi.oaixiv.org>，
Cloudflare Worker）。切到「静态快照」则可以只依赖 GitHub Pages 的 JSON 文件离线体验。

<div class="pg" id="playground">
  <div class="pg-row pg-modes">
    <label class="pg-mode">
      <input type="radio" name="pg-mode" value="live" checked>
      <span>实时 API（Worker）</span>
    </label>
    <label class="pg-mode">
      <input type="radio" name="pg-mode" value="static">
      <span>静态快照（GitHub Pages）</span>
    </label>
    <input id="pg-base" class="pg-input pg-base" type="url"
           value="https://bookapi.oaixiv.org" spellcheck="false">
  </div>

  <div class="pg-row">
    <select id="pg-endpoint" class="pg-select">
      <option value="latest">最新图书 /books/latest</option>
      <option value="tag">标签图书 /books/tag</option>
      <option value="detail">图书详情 /books/{id}</option>
      <option value="search">关键词搜索 /search</option>
    </select>
    <input id="pg-a" class="pg-input" placeholder="type=全部" spellcheck="false">
    <input id="pg-b" class="pg-input pg-short" placeholder="page=0" spellcheck="false">
    <button id="pg-send" class="pg-btn">发送请求</button>
  </div>

  <div class="pg-status" id="pg-status">就绪</div>
  <pre class="pg-output" id="pg-output">// 响应会显示在这里</pre>
  <div class="pg-hint">
    实时 API 带 TTL 缓存与限流，请勿高频调用；静态快照由 GitHub Actions 每 6 小时刷新，
    搜索在浏览器端对索引做过滤，结果可能不完整。
  </div>
</div>

<script src="../assets/playground.js"></script>
