# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /app

# 先装依赖，最大化利用构建缓存
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . "gunicorn>=21.2" \
    && (pip install --no-cache-dir "orjson>=3.9" || echo "orjson 不可用，回退标准库 json") \
    && (pip install --no-cache-dir "quickjs>=1.19" || echo "quickjs 不可用，跳过旧版解密回退")

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2).status==200 else 1)"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "douban_api.app:create_app()"]
