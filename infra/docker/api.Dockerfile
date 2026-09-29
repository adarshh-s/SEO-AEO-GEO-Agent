# API image. `dev` target is used by docker-compose (source mounted, reload);
# `prod` is the deployable image (Railway). Hardened further in Phase 6.
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH"
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv
WORKDIR /repo
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/worker/pyproject.toml apps/worker/pyproject.toml
RUN uv sync --frozen --no-dev --package app-api --no-install-workspace
COPY config config
COPY packages/core packages/core
COPY apps/api apps/api
RUN uv sync --frozen --no-dev --package app-api
WORKDIR /repo/apps/api

FROM base AS dev
WORKDIR /repo

FROM base AS prod
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app_api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
