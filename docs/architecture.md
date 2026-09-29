# QuardLink architecture

Status: approved after Phase 0 review. **[D#]** tags refer to decisions in
[decisions.md](decisions.md) (all resolved).

## 1. System overview

```
                         ┌──────────────── customers' websites ────────────────┐
                         │ agent.js snippet · WP plugin · Shopify app embed ·  │
                         │ sdk-js · edge worker · (Wix/Webflow/Salla/Zid APIs) │
                         └───────┬───────────────────────────────▲─────────────┘
                   public fixes  │ events (referrals, bots)      │ platform APIs
                   (cached, RO)  ▼                               │ (OAuth)
┌──────────┐  HTTPS  ┌─────────────────────────┐  enqueue  ┌─────┴──────────────────────┐
│ apps/web │ ──────► │ apps/api  (FastAPI)      │ ────────► │ apps/worker (Celery prefork)│
│ React SPA│ cookies │ auth · tenancy · CRUD ·  │  Redis    │ crawl/render (Playwright) · │
└──────────┘         │ public API · webhooks ·  │ ◄──────── │ rank + AI checks · diagnose │
                     │ quota/cost gate          │  results  │ fix gen · deploy · reports  │
                     └──────────┬──────────────┘           └──────┬──────────────────────┘
                                │ SQLAlchemy                      │ same models package
                          ┌─────▼─────┐   ┌───────┐   ┌───────────▼───────────┐
                          │ Postgres16│   │ Redis │   │ S3 (PDFs, snapshots)   │
                          └───────────┘   └───────┘   └────────────────────────┘
                                        Celery Beat → schedules
External: Anthropic · OpenAI · Perplexity · Gemini · DataForSEO · PSI/CrUX · GSC · Resend  (payments: Phase 7)
```

- **API** is stateless and never fetches customer URLs itself (see the
  claude-seo `url_safety` constraint in [claude-seo-mapping.md](claude-seo-mapping.md#critical-constraint-url_safety-is-process-global)).
- **Workers** run on the `prefork` pool with separate queues so Chromium jobs
  can't starve cheap jobs:
  `crawl` (Playwright, low concurrency, high memory) · `tracking` (SERP + AI
  checks, rate-limited per provider) · `agents` (LLM diagnosis/fix gen) ·
  `deploy` (platform connector writes) · `default` (email, reports, housekeeping).
- **Beat** enqueues per-site schedules derived from the plan's check frequency.
  One beat instance; schedules stored in DB (a `celery-sqlalchemy-scheduler`-style
  or custom DB-driven dispatcher that runs every 5 min and enqueues due sites),
  so schedules change without a redeploy.

## 2. Monorepo layout

```
/
├── CLAUDE.md  THIRD_PARTY_NOTICES.md  LICENSE  README.md
├── config/
│   └── brand.json                 # SINGLE source of product naming (decision #1)
├── apps/
│   ├── web/                       # React 18 + Vite + TS
│   │   ├── src/
│   │   │   ├── app/               # router, providers, layout, RTL switch
│   │   │   ├── features/          # onboarding, dashboard, keywords, ai-visibility,
│   │   │   │                      # diagnosis, fixes, audits, reports, integrations, settings
│   │   │   ├── components/ui/     # shadcn/ui
│   │   │   ├── lib/               # api client (generated from OpenAPI), i18n, brand
│   │   │   └── locales/{en,ar}/*.json
│   │   └── tests/                 # Vitest + RTL; e2e/ (Playwright)
│   ├── api/
│   │   ├── app_api/               # neutral internal name (D1)
│   │   │   ├── main.py  settings.py  deps.py (auth, tenant context)
│   │   │   ├── routers/           # auth, orgs, sites, keywords, prompts, checks, fixes,
│   │   │   │                      # audits, reports, integrations, plans, admin, public_v1
│   │   │   ├── services/          # business logic (quota, cost ceiling, verification…)
│   │   │   ├── integrations/<platform>/   # PlatformConnector impls (wix, webflow, salla, zid, shopify, wordpress, github, gsc)
│   │   │   └── providers/         # LLMProvider, SerpProvider, PaymentProvider, EmailProvider, StorageProvider
│   │   ├── alembic/
│   │   └── tests/
│   └── worker/
│       ├── app_worker/
│       │   ├── celery_app.py  beat.py
│       │   ├── tasks/             # crawl, detect, rank, ai_visibility, score, diagnose,
│       │   │                      # generate_fixes, deploy, audit, report, cost_rollup
│       │   ├── seo_engine/        # thin adapter over vendor/claude-seo (+ platform_rules/)
│       │   └── agents/prompts/    # adapted system prompts (with upstream attribution)
│       └── tests/
├── packages/
│   ├── core/  (app_core)          # shared Python: SQLAlchemy models, Pydantic schemas, enums,
│   │                              # brand loader, cost/quota primitives (used by api + worker)
│   ├── snippet/                   # agent.js (TS, esbuild, <15 KB gz)
│   ├── sdk-js/                    # npm: core client + /next /react /nuxt /astro entry points
│   ├── wp-plugin/                 # PHP
│   ├── shopify-app/               # Remix app + theme app extension
│   └── edge-worker/               # Cloudflare Worker template
├── vendor/claude-seo/             # git submodule, pinned
├── scripts/brand-sync.*           # generates brand constants for py/ts/php
├── infra/                         # Dockerfiles, docker-compose.yml, deploy guides
├── docs/                          # this folder
└── .github/workflows/             # ci.yml (lint, type-check, tests per app)
```

Python tooling: `uv` workspace (`packages/core`, `apps/api`, `apps/worker`).
JS tooling: `pnpm` workspace (`apps/web`, `packages/snippet`, `sdk-js`,
`shopify-app`, `edge-worker`). **[D5]**

## 3. Central brand config (decision #1)

`config/brand.json` is the only place product naming lives:

```json
{
  "product_name": "QuardLink",
  "brand_slug": "quardlink",
  "snippet_global": "QuardLink",
  "verification_meta_name": "quardlink-verification",
  "...": "see config/brand.json"
  // hosts are NOT in brand.json; they come from env (APP_URL, API_URL, CDN_URL)
}
```

- `scripts/brand-sync` generates `packages/core/.../brand.py`,
  `apps/web/src/lib/brand.ts`, `packages/snippet/src/brand.ts`,
  `packages/sdk-js/src/brand.ts`, `packages/wp-plugin/includes/brand.php`, and
  patches `package.json` names and the WP plugin header. CI runs
  `brand-sync --check` and fails on drift.
- The i18n strings interpolate `{{product}}` rather than containing the name.
- Things that **can't** be renamed painlessly once published (npm package name,
  WP plugin slug, Shopify app handle, snippet global, verification meta name)
  are marked in the file with `"_frozen_after_launch"`. Rename before publishing
  them, which is the latest point the product name must be final. **[D1]**
- Internal Python packages use neutral names (`app_api`, `app_worker`,
  `app_core`), so a rename never touches them. **[D1]**

## 4. Multi-tenancy

- Every tenant-owned table has `org_id` (denormalized onto child tables such as
  `keywords`, `rank_checks`, `ai_checks` and `fixes`, not only through
  `site_id`), so every query can filter by it directly and we can add Postgres
  RLS later.
- **Enforcement in two layers:**
  1. Repository/query helpers require a `TenantContext` (org_id from the JWT
     membership) and add `WHERE org_id = :ctx`. Raw session access in routers is
     lint-banned.
  2. **Postgres Row-Level Security** policies keyed on
     `current_setting('app.org_id')`, set per transaction. This is defence in
     depth: a forgotten filter returns nothing instead of leaking. Workers set
     the same setting per task. **[D6]**
- Tests: a parametrized test hits **every** router endpoint as org B against
  org A's resources and asserts 404. Endpoints are auto-discovered from the
  FastAPI route table, so new endpoints are covered automatically.
- Public endpoints (`/public/v1/*`) authenticate with the site key (read-only,
  approved + sanitized fixes only) or a scoped API key.

## 5. Quotas, cost tracking and the cost ceiling (decision #4)

```
task wants paid call ──► CostGate.reserve(org, provider, est_cost, essential?)
                             │ 1. plan quota check (counts: keywords, prompts, audits…)
                             │ 2. monthly $ ceiling: spent + reserved + est ≤ ceiling?
                             │    ├─ ≥100% and !essential → DENY (task marks "paused_budget")
                             │    └─ crosses 80% → emit budget.warning (once per period)
                             ▼
                        provider call ──► CostGate.settle(actual_cost from usage/tokens)
```

- `usage_counters` holds per-org, per-period counts. `api_cost_events` stores one
  row per paid call (org, site, provider, model, units, tokens, cost_usd,
  task_id, idempotency key). Monthly totals are rolled up and cached in Redis for
  fast gating (atomic `INCRBYFLOAT` reservations, reconciled with Postgres
  nightly).
- `org_cost_limits`: `monthly_ceiling_usd` (default from plan),
  `override_ceiling_usd` (set by platform admin), `warned_80_at`,
  `paused_at`.
- **Essential vs non-essential**: non-essential = scheduled rank checks,
  scheduled AI checks, scheduled audits, prompt/keyword suggestions.
  Essential = user-initiated single actions (diagnosis, fix generation the user
  clicked, **[D7]**), onboarding detection, deploy/rollback. Essential calls are
  still capped by a hard stop (e.g. 120% of ceiling) to prevent runaway spend.
  **[D7]**
- At 80%: email + in-app notice to org owners/admins, plus an email to the
  platform operator address (`OPS_ALERT_EMAIL`) and an admin-panel flag. At
  100%: pause non-essential schedules, show a banner, notify both. The org admin
  sees "ask to raise the limit"; a **platform admin** raises it in the admin panel.
  **[D8]**
- Cost estimates: DataForSEO priced per task (standard queue ~$0.0006/SERP page
  of 10 results, live ~$0.002; verify at build time). LLM costs computed from
  token usage × a per-model price table in DB (not hard-coded), editable in admin.

## 6. Provider interfaces

`packages/core` defines Protocols; implementations live in `apps/*/providers`:

- `LLMProvider.complete(messages, model_role: "main"|"fast", schema?) -> LLMResult(text, json, usage, cost)`
- `AnswerEngine.ask(prompt, language, country) -> EngineAnswer(text, citations[], model, usage, cost)`,
  with implementations `openai_web`, `perplexity`, `gemini_grounded`,
  `claude_web_search`, and optionally `dataforseo_llm` **[D3]**
- `SerpProvider.rank(keyword, lang, location, device) -> SerpResult(position, url, features, ai_overview{present, cites_site, refs})`
- `PlatformConnector` (per platform): `capabilities()`, `verify_ownership()`,
  `read_current(target)`, `apply(fix) -> DeployResult(previous_state)`,
  `rollback(deploy)`, `health()`
- `PaymentProvider` (interface only until Phase 7), `EmailProvider`, `StorageProvider`

Every implementation has a fake used in tests and in `SEED_DEMO` mode.
Model IDs come from env (`CLAUDE_MODEL_MAIN`, `CLAUDE_MODEL_FAST`,
`OPENAI_MODEL`, `PERPLEXITY_MODEL`, `GEMINI_MODEL`).

## 7. Core pipelines

**Onboarding detection** (API → `crawl` queue, wait ≤ 20 s then poll): fetch
homepage raw + rendered → platform fingerprint (generator meta, asset hosts,
globals, headers, URL patterns) → `rendering` from the diff → `<html lang>` +
hreflang → brand name (og:site_name, title, Organization schema) → city/
industry (schema, contact page, fast LLM) → competitor suggestions (DataForSEO
SERP overlap for seed keywords, or LLM, **[D3]**) → robots.txt AI-bot report.

**Tracking cycle** (per site, per schedule): quota/cost gate → SERP per keyword
(DataForSEO standard queue + postback/poll) → AI checks: prompt × engine × N
runs → parse each answer with the fast model into structured JSON + deterministic
brand/domain matching (fuzzy + normalized Arabic: strip diacritics/tatweel, unify
alef/yaa/taa-marbuta variants) → aggregate into `visibility_scores` → emit
`score.changed`.

**Diagnosis**: target (keyword|prompt) → our page (raw+rendered) + top
competitor pages (ranking URLs or cited URLs) → deterministic diffs (schema
types, headings, word count, answer-first presence, JS-only content, CWV,
AI-bot access, hreflang) + platform rules → main-model agent with adapted prompts
→ findings JSON → fix drafts.

**Fix lifecycle**: `draft → approved → deploying → deployed | failed → rolled_back`, and `draft → rejected`.
Every payload runs through a sanitizer before being stored as approved and again
before being served: JSON-LD parsed and re-serialized, `</script` escaped, type
allowlist; HTML blocks via an allowlist sanitizer (nh3); meta lengths bounded.
Deploy picks the connector by `recommended_delivery` and site integrations,
reads the current state first (merge/replace, no duplicates), stores
`previous_state`, and writes `audit_log`.

## 8. i18n

- UI: react-i18next, namespaces per feature, `en` source, `ar` partial with
  fallback to `en`. `<html lang dir>` set from the user's `ui_language`. Tailwind
  logical utilities (`ms-*`, `pe-*`, `start-*`) enforced by an ESLint rule that
  bans `ml-/mr-/pl-/pr-/left-/right-` classes. Arabic font: IBM Plex Sans Arabic
  or Noto Sans Arabic. Numbers stay Western digits by default **[D9]**. Recharts
  are mirrored in RTL.
- Server: user-facing text generated server-side (emails, PDFs, platform
  instructions, notifications) uses Python gettext-style catalogs (`babel`)
  with the same locale codes. LLM-generated text gets an explicit language
  instruction plus a post-check (script detection) with one retry.
- Adding a language = add `locales/<code>/*.json` + backend catalog + add the
  code to `SUPPORTED_UI_LANGUAGES`, with no code changes. RTL-ness comes from
  `Intl.Locale(...).textInfo` / a small RTL list.

## 9. Security highlights

- Auth: argon2id passwords, short-lived access JWT (15 min) + rotating refresh
  token (httpOnly, Secure, SameSite=Lax cookies) with reuse detection. CSRF:
  double-submit token for cookie-authenticated mutating requests. Google sign-in
  via OIDC.
- Secrets at rest: `integrations.encrypted_credentials` sealed with envelope
  encryption (a data key per row, wrapped by `APP_ENCRYPTION_KEY`, versioned for
  rotation). API keys: `prefix.secret`, SHA-256 hashed (high-entropy secret, so
  no slow hash needed), shown once.
- Rate limits (Redis, sliding window): auth endpoints, public fixes endpoint
  (per site key + IP; responses cached at the CDN), events ingest.
- Webhooks in: signature verification per provider (Shopify HMAC, Wix JWT,
  Salla/Zid per docs; payment providers in Phase 7). Webhooks out: HMAC-SHA256 signature + timestamp,
  retries with backoff, and SSRF checks on customer webhook URLs (same
  `url_safety`, worker-side).
- Idempotency: every task keyed (`site_id:type:period`), Celery `acks_late` +
  DB unique constraints.

## 10. Environments & deploy

- Local: `docker compose up` → postgres, redis, api, worker (crawl +
  tracking queues), beat, web, mailpit (local email), minio (S3).
- Prod: web on Vercel/Netlify; api/worker/beat as Docker images (a Playwright
  base image for the crawl worker) on Railway **[D10]**;
  managed Postgres + Redis.
- Observability: structlog JSON logs with `org_id`/`site_id`/`task_id`,
  Sentry (only if `SENTRY_DSN` is set, **[D11]**), a per-org cost dashboard in admin.

## 11. Implementation notes (Phase 1)

- **Sync SQLAlchemy 2 + psycopg 3** in both API and workers (FastAPI runs sync endpoints in
  its threadpool). One model/session layer shared with Celery, no async/sync duplication.
- **RLS mechanics**: migrations run as the owner role; tenant request sessions switch to the
  `app_tenant` role per transaction (`SET LOCAL ROLE`) and set `app.org_id` / `app.user_id`.
  System sessions (auth, `/me`, platform admin, seeding, schedulers) stay on the owner role
  and bypass RLS on purpose. A new org-owned table must get a policy in its migration, and
  `tests/test_rls.py` fails otherwise. On Railway the default Postgres user can create roles;
  if a managed Postgres forbids `CREATE ROLE`, create `app_tenant` once manually.
- **CSRF**: the token is in an httpOnly cookie and returned in JSON by login/refresh/me; the SPA
  keeps it in memory and echoes it in `X-CSRF-Token`. Works across `app.`/`api.` subdomains
  without a shared-domain readable cookie.
- **Frontend toolchain**: TypeScript pinned to 6.0.x because typescript-eslint doesn't
  support 7.x yet. Tailwind v4 (CSS-first config). shadcn/ui-style components are written in
  `components/ui` (same pattern as the shadcn CLI output).
- **E2E** runs on dedicated ports (API 8100, web 5273) so it never hits another dev server.

