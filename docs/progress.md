# Progress

## Phase 0: Plan (done 2026-09-29)
- Spec saved as `CLAUDE.md`; claude-seo added as a pinned submodule (`ff87fce`).
- `docs/claude-seo-mapping.md`, `docs/platforms/*.md`, `docs/architecture.md`, `docs/decisions.md`.
- Review decisions recorded (D1–D20). **Payments moved to a final Phase 7** (no payment code
  before then; manual plan assignment; Trial plan for new orgs).
- `docs/registrations-checklist.md` lists every external registration (none exist yet).

## Phase 1: Foundation (done 2026-09-29, awaiting review)

**Built**
- **Monorepo**: uv workspace (`packages/core` = `app_core`, `apps/api` = `app_api`,
  `apps/worker` = `app_worker`) + pnpm workspace (`apps/web`). Neutral internal names (D1).
- **Brand**: `config/brand.json` (QuardLink) → `scripts/brand_sync.py` generates Python and TS
  constants; CI fails on drift. Snippet namespace, verification meta tag, plugin slug, npm
  scope, site-key prefix and crawler UA all come from it.
- **Database**: Alembic migrations `0001` (users, orgs, memberships, invitations, plans,
  subscriptions placeholder, sites, keywords, prompts, audit_log) and `0002` (default plans:
  Trial, Starter, Growth, Business). **Postgres RLS** (D6): `app_tenant` role, policies on every
  org-owned table, tenant sessions `SET LOCAL ROLE` + `app.org_id` per transaction.
- **Auth**: email/password (argon2id), access JWT + rotating refresh tokens with reuse
  detection (httpOnly SameSite=Lax cookies), CSRF double-submit, email verification, password
  reset (single-use), Google sign-in (OIDC + PKCE + nonce; links verified emails), Redis rate
  limits. Production refuses to start with the dev JWT secret or insecure cookies.
- **Orgs & roles**: owner/admin/member/viewer, invitations by email (EN/AR emails), last-owner
  protection, org switching, audit log for sensitive actions.
- **Sites / keywords / prompts**: CRUD with plan limits (sites, keywords, prompts, languages
  per site, Arabic add-on), URL normalization (rejects IPs/localhost/internal hosts),
  language must be enabled on the site, dedupe.
- **Plans without payments** (D20): new orgs → Trial; platform admin assigns plans, add-ons and
  cost-ceiling overrides (`/admin/*` + minimal admin page). `PaymentProvider` interface only.
- **Onboarding API**: analyze / suggestions are **Phase 1 mocks** behind `SiteAnalyzer` /
  `SuggestionProvider` interfaces (clearly labelled "sample data" in the UI); `complete`
  creates site + keywords + prompts atomically.
- **Worker**: Celery app with `default/crawl/tracking/agents/deploy` queues, prefork pool,
  acks-late; beat schedule with a refresh-token cleanup task.
- **Web app**: React 18 + Vite + Tailwind v4 + shadcn-style components, TanStack Query,
  Zustand, react-hook-form + zod. i18n with **English default, Arabic optional**: locales are
  discovered from `src/locales/<lang>/`, missing keys fall back to English, RTL only for Arabic,
  Western digits (D9), choice saved per user. ESLint rule bans left/right-only Tailwind
  classes. Pages: landing, pricing ("Contact us"), integrations, privacy/terms drafts, login,
  signup, forgot/reset password, verify email, accept invite, app shell (responsive sidebar,
  org switcher, language toggle), overview, onboarding wizard (6 steps; platform-specific
  connect options with the honest snippet limitation), websites list + site settings
  (languages, brand spellings, competitors, keywords, prompts), settings (profile + interface
  language, organization + plan usage, team), admin, placeholders for later sections.
  API types generated from OpenAPI.
- **Infra**: `docker-compose.yml` (postgres, redis, api, worker, beat, web, mailpit, minio),
  Dockerfiles (dev + prod targets), complete `.env.example`, GitHub Actions CI (lint, brand
  drift, migration drift, OpenAPI drift, tests, build, E2E).
- **Seed** (`SEED_DEMO=true`): demo org (Business plan) with a WordPress site (EN), a Next.js
  site (EN) and a Salla store with Arabic enabled; owner, viewer and platform-admin accounts.

**Tests**: 63 pytest (incl. tenant isolation across **every** endpoint, auto-discovered from
OpenAPI, plus DB-level RLS tests), 13 Vitest, 1 Playwright E2E (signup → onboarding → site
listed → Arabic RTL persists after reload). All passing locally. CI workflow written but not
run yet (no GitHub remote).

**Bugs found and fixed by the tests**: comma-separated `CORS_ORIGINS` crashed settings
parsing; the overview redirected back to onboarding right after finishing (stale cache).

## Phase 2: Crawling & tracking (not started)
