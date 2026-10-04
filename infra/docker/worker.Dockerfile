# Worker + beat image (Celery, prefork). Runs as a long-lived container, never serverless
# (CLAUDE.md §3): jobs are long and need headless Chromium.
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv
WORKDIR /repo
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/worker/pyproject.toml apps/worker/pyproject.toml
RUN uv sync --frozen --no-dev --package app-worker --no-install-workspace
# Headless Chromium + its system libraries for raw-vs-rendered checks.
RUN playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*
COPY config config
# claude-seo (MIT): SSRF protection and SEO scripts. Workers refuse to start without it.
COPY vendor/claude-seo/scripts vendor/claude-seo/scripts
COPY vendor/claude-seo/LICENSE vendor/claude-seo/LICENSE
COPY packages/core packages/core
COPY apps/worker apps/worker
RUN uv sync --frozen --no-dev --package app-worker \
    && python -c "import app_worker.seo_engine.url_safety"

FROM base AS dev

FROM base AS prod
RUN useradd --create-home --uid 10001 app && chmod -R a+rX /opt/ms-playwright
USER app
CMD ["celery", "-A", "app_worker.celery_app", "worker", "--pool=prefork", "--concurrency=2", "-Q", "default,crawl,tracking,agents,deploy", "--loglevel=INFO"]
