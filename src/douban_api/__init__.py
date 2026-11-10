"""豆瓣图书查询 API.

快速开始::

    from douban_api import create_app
    app = create_app()

命令行::

    python -m douban_api serve --port 5000
    python -m douban_api snapshot --out site
"""

from __future__ import annotations

from .app import create_app
from .config import Settings
from .service import DoubanService
from .version import __version__

__all__ = ["DoubanService", "Settings", "__version__", "create_app"]
