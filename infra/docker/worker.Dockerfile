# Worker + beat image. Phase 2 switches the base to a Playwright image (Chromium) and
# adds vendor/claude-seo; workers must run on containers, never serverless (CLAUDE.md §3).
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH"
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv
WORKDIR /repo
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/worker/pyproject.toml apps/worker/pyproject.toml
RUN uv sync --frozen --no-dev --package app-worker --no-install-workspace
COPY config config
COPY packages/core packages/core
COPY apps/worker apps/worker
RUN uv sync --frozen --no-dev --package app-worker

FROM base AS dev

FROM base AS prod
RUN useradd --create-home --uid 10001 app
USER app
CMD ["celery", "-A", "app_worker.celery_app", "worker", "--pool=prefork", "--concurrency=2", "-Q", "default,crawl,tracking,agents,deploy", "--loglevel=INFO"]
