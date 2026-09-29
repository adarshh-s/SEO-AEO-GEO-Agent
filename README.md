# QuardLink

Multi-tenant SaaS that helps businesses rank in Google and get mentioned in AI answers
(ChatGPT, Gemini, Perplexity, Claude, AI Overviews): **track → diagnose → fix → report**.
"QuardLink" is a working name; all naming comes from [`config/brand.json`](config/brand.json).

The product spec is [CLAUDE.md](CLAUDE.md). Design docs are in [docs/](docs/):
[architecture](docs/architecture.md), [decisions](docs/decisions.md),
[progress](docs/progress.md), [platform research](docs/platforms/README.md),
[claude-seo mapping](docs/claude-seo-mapping.md),
[registrations checklist](docs/registrations-checklist.md).

## Layout

```
apps/api        FastAPI (app_api) + Alembic migrations
apps/worker     Celery workers + beat (app_worker)
apps/web        React 18 + Vite + Tailwind v4 + react-i18next (English default, Arabic optional)
packages/core   Shared Python: models, settings, tenancy/RLS, brand, i18n (app_core)
config/         brand.json (single source of product naming)
vendor/         claude-seo (git submodule, MIT)
```

## Run locally

Prerequisites: Docker, [uv](https://docs.astral.sh/uv/), Node 22+ with pnpm 10.

```bash
git submodule update --init
cp .env.example .env
docker compose up --build        # web :5173, api :8000, mailpit :8025
```

Demo data is seeded (`SEED_DEMO=true` in compose):

| Account | Password | |
|---|---|---|
| demo@example.com | demo-password-123 | Owner of "Demo Company" (Business plan, 3 sites incl. one with Arabic) |
| viewer@example.com | demo-password-123 | Viewer in the same org |
| admin@example.com | demo-password-123 | Platform admin (`/app/admin`: assign plans manually) |

If port 5173 is taken: `WEB_PORT=5174 docker compose up`.

Without Docker for the apps (Postgres/Redis still via compose):

```bash
docker compose up -d postgres redis mailpit
uv sync && uv run alembic -c apps/api/alembic.ini upgrade head
SEED_DEMO=true uv run python -m app_api.seed
uv run uvicorn app_api.main:app --reload            # API on :8000
pnpm install && pnpm --filter web dev               # web on :5173
```

## Tests and checks

```bash
uv run pytest                                  # API, worker, core (needs Postgres from compose)
uv run ruff check apps packages scripts && uv run black --check apps packages scripts
pnpm --filter web test                         # Vitest + Testing Library
pnpm --filter web lint && pnpm --filter web typecheck
pnpm --filter web exec playwright install chromium && pnpm --filter web e2e   # E2E on ports 8100/5273
```

## Generated files (never edit by hand)

```bash
python scripts/brand_sync.py   # brand constants for Python + TS, from config/brand.json
pnpm gen:api                   # openapi.json + apps/web/src/lib/api-types.gen.ts
```

CI (`.github/workflows/ci.yml`) fails if either is stale.
