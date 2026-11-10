"""gunicorn 配置：gthread 多线程，适合以网络等待为主 IO 的爬虫型服务。

用法：gunicorn -c gunicorn.conf.py douban_api.app:create_app()
"""

import multiprocessing
import os

wsgi_app = "douban_api.app:create_app()"
bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '5000')}"

# 每个 worker 8 线程：单进程内可并发等待上游，内存占用远低于多进程
workers = int(os.getenv("WEB_CONCURRENCY", str(min(4, multiprocessing.cpu_count() or 1))))
threads = int(os.getenv("GUNICORN_THREADS", "8"))
worker_class = "gthread"
preload_app = True

# 容器里用 tmpfs 减少心跳文件的磁盘抖动；macOS / 无 /dev/shm 的环境自动跳过
_SHARED_MEMORY = "/dev/shm"
if os.path.isdir(_SHARED_MEMORY) and os.access(_SHARED_MEMORY, os.W_OK):
    worker_tmp_dir = _SHARED_MEMORY

timeout = 30
graceful_timeout = 20
keepalive = 5
max_requests = 2000
max_requests_jitter = 200

accesslog = os.getenv("ACCESS_LOG", "-")
errorlog = os.getenv("ERROR_LOG", "-")
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(L)ss %(D)µs "%(a)s"'
