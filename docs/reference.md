# 完整参考（OpenAPI）

由代码中的 `src/douban_api/openapi.py` 生成，CI 会校验 `docs/openapi.json` 与代码一致。

<div id="redoc-container" class="redoc-wrap"></div>

<script src="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js"></script>
<script>
  document.addEventListener("DOMContentLoaded", function () {
    if (window.Redoc) {
      Redoc.init(
        "../openapi.json",
        {
          expandResponses: "200,400,404,429,502",
          hideDownloadButton: false,
          theme: { colors: { primary: { main: "#0a7d4f" } }, typography: { fontSize: "15px" } }
        },
        document.getElementById("redoc-container")
      );
    }
  });
</script>

如果上面的渲染器没有加载（例如离线环境），可以直接下载原始文件：
<a href="../openapi.json" target="_blank" rel="noopener">openapi.json</a>，
或使用 Swagger UI：`/docs`（Flask 服务内置）。
