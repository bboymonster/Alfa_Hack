# 03-ai-service: FastAPI + LangGraph + embedded Qdrant + Tesseract OCR (rus/eng).
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    AI_ARTICLES_DIR=/data/articles \
    AI_DATASETS_DIR=/data/datasets \
    AI_INDEX_DIR=/data/index \
    FASTEMBED_CACHE_PATH=/data/index/models

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY evals ./evals
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data/articles /data/datasets /data/index \
    && chown -R app:app /data /app
USER app

EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=4)"

CMD ["uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
