"""向后兼容入口：``python api.py`` 仍然可用。

真正的代码在 ``src/douban_api/``。保留本文件是为了不破坏已有部署脚本/文档。
生产环境建议使用 gunicorn：

    gunicorn -c gunicorn.conf.py douban_api.app:create_app()
"""

from __future__ import annotations

from douban_api import create_app

app = create_app()

if __name__ == "__main__":
    settings = app.extensions["douban_settings"]
    app.run(host=settings.host, port=settings.port, debug=settings.debug, threaded=True)
