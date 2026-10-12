# syntax=docker/dockerfile:1
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
# Downloaded at the commit the vendor/claude-seo submodule pins, because hosted builders
# (Railway) don't check out submodules. Keep this in sync: `git ls-files -s vendor/claude-seo`.
ARG CLAUDE_SEO_COMMIT=ff87fcee0734845d3f59128c8c905799ee2298da
RUN python - <<EOF
import io, shutil, tarfile, urllib.request
url = "https://github.com/AgriciDaniel/claude-seo/archive/${CLAUDE_SEO_COMMIT}.tar.gz"
with urllib.request.urlopen(url, timeout=60) as r:
    tarfile.open(fileobj=io.BytesIO(r.read())).extractall("/tmp/claude-seo", filter="data")
src = "/tmp/claude-seo/claude-seo-${CLAUDE_SEO_COMMIT}"
shutil.copytree(src + "/scripts", "vendor/claude-seo/scripts")
shutil.copy(src + "/LICENSE", "vendor/claude-seo/LICENSE")
shutil.rmtree("/tmp/claude-seo")
EOF
COPY packages/core packages/core
COPY apps/worker apps/worker
RUN uv sync --frozen --no-dev --package app-worker \
    && python -c "import app_worker.seo_engine.url_safety"

FROM base AS dev

FROM base AS prod
RUN useradd --create-home --uid 10001 app && chmod -R a+rX /opt/ms-playwright
USER app
CMD ["celery", "-A", "app_worker.celery_app", "worker", "--pool=prefork", "--concurrency=2", "-Q", "default,crawl,tracking,agents,deploy", "--loglevel=INFO"]
