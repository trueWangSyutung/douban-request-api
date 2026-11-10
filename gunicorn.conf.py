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
worker_tmp_dir = "/dev/shm"
preload_app = True

timeout = 30
graceful_timeout = 20
keepalive = 5
max_requests = 2000
max_requests_jitter = 200

accesslog = os.getenv("ACCESS_LOG", "-")
errorlog = os.getenv("ERROR_LOG", "-")
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(L)ss %(D)µs "%(a)s"'
