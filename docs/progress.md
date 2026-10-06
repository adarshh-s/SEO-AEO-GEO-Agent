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

## Phase 2: Crawling & tracking (done)

- Platform fingerprinting, raw vs rendered HTML scraping with Playwright, and robots.txt AI-bot detection.
- SERP rank tracking via DataForSEO; AI visibility tracking across ChatGPT, Gemini, Claude, and Perplexity.
- Normalization and brand detection (including Arabic normalization: diacritics, tatweel, letter unification).
- Visibility scoring engine and scheduling via Celery Beat.
- Per-org monthly cost guard with soft alert (80%), non-essential work pause (100%), and hard cap (120%).
- Frontend dashboards for Overview, Keywords, AI Visibility, and Cost alerts.

## Phase 3: Diagnose & fix (done)

- Deterministic diff diagnostics comparing target pages with top competitor pages.
- Template-based fix generator for schema (JSON-LD), meta tags, headings, content and FAQ blocks in the target page's language. **No LLM is called yet** (diagnosis and fixes are deterministic).
- HTML/JSON-LD sanitization: claimed here originally, but only a bypassable regex existed. Real `nh3` allowlist sanitizer added in the 2026-10-04 review (see below).
- Fix lifecycle and review inbox (`draft -> approved -> deploying -> deployed | failed -> rolled_back`).
- Universal JavaScript snippet with AI crawler visit analytics and edge caching.
- Site ownership verification (meta tag, file placement, DNS TXT) and public API / webhooks.

## Phase 4: Deep platform integrations (done)

- Connectors and automatic delivery: WordPress plugin, Shopify App (theme app extension), Next.js / React SDK (`@quardlink/sdk`), GitHub PR creator (`@octokit/rest`), Cloudflare Edge Worker (`@cloudflare/workers-types`), Google Search Console integration, Webflow connector, and Wix connector.
- Dynamic fallback to manual/snippet delivery if connectors are not connected.

## Phase 5: Audits, reports, and Saudi platforms (done)

- Full site technical SEO audits with automated scoring (0-100) and issue categorize/severity trees.
- PDF executive report generator (WeasyPrint) with bilingual English/Arabic layout support.
- Scheduled weekly email digests (Resend / SMTP) sent to org admins.
- Salla and Zid e-commerce platform connectors with merchant onboarding instructions and OAuth scaffolding.

## Phase 6: Launch readiness (done, awaiting review)

- Public website: landing page with interactive FAQ, platform ticker, and feature walkthrough; pricing page with Growth badge and direct "Contact Us" routing (`adarshs18400@gmail.com`); integrations directory with category filter chips.
- Platform Admin Console (`/app/admin`): 4 functional tabs (Organizations & Plans, API Costs & Providers with live spending gauges, Plan Configurations editor, and Platform Audit Logs).
- Production deployment setup: `docker-compose.prod.yml`, `infra/docker/web.Dockerfile`, `infra/nginx/spa.conf`, `infra/nginx/nginx.conf`.
- Pre-flight validation script: `scripts/verify_prod_env.py` checking secrets, DB connectivity, PostgreSQL `app_tenant` RLS role, Redis, email providers, and production domain compliance.
- Complete production deployment guide in `docs/deployment.md`.

## Review & security fixes (2026-10-04)

Phases 2–6 and the OmniRank rename were reviewed against CLAUDE.md. An uncommitted, half-finished
revert that broke imports was found in the working tree and stashed (`git stash list`), not deleted.

**Fixed**
- **Remote code execution**: the worker's HTTP `/tasks/{module.function}` endpoint (added for a
  Vercel serverless setup) imported and ran any Python function with caller-supplied args, with no
  auth. Removed, together with `vercel.json` services for api/worker; workers are Celery
  containers again (spec §3, D10). Vercel remains the frontend host.
- **Stored XSS on customers' sites**: fix HTML went into `innerHTML` unsanitized; JSON-LD was
  written into `<script>` unescaped (Cloudflare worker, SDK). Now: `app_core/sanitize.py` (nh3
  allowlist, JSON-LD validation, `<`/`>`/`&` escaping), enforced on every write via the `Fix`
  model and again when serving; approved fixes can't be edited without re-review.
- **Wrong schema output**: Cloudflare worker, WordPress plugin and SDK emitted the whole payload
  (`{"json_ld": …}`) instead of the JSON-LD; WordPress printed schema twice with Yoast/Rank Math.
- **SSRF**: webhooks, ownership verification (in the API), the WordPress connector and the
  Shopify connector (any domain with a dot received the admin token) fetched customer URLs
  unprotected; Playwright had no route guard; the claude-seo wrapper silently fell back to a weak
  check. Now: claude-seo's guard in workers (fail-closed, route handler for Chromium),
  `app_core/net.py` thread-safe pinned-IP guard for the API, Shopify restricted to `*.myshopify.com`.
- **Credentials in plaintext**: platform tokens and webhook secrets are now Fernet-encrypted at
  rest (`APP_ENCRYPTION_KEY`, rotation supported, migration `0007`); webhook secrets are shown once.
- **Fake data in production**: missing API keys made every provider silently return random mock
  answers/rankings. Mocks are now local/test only; production skips unconfigured providers.
- **Real providers could never run**: their settings fields didn't exist (AttributeError). Added.
  Model IDs are env-only (hard-coded `gpt-4o` / `claude-3-5-haiku-latest` fallbacks removed).
- **Rank tracking used Saudi Arabia for every non-US country**; now a proper country → location map.
- **Worker image** had no Chromium and no claude-seo, so JS-only detection could never work and
  rendering failed silently. Image now ships both (verified: real crawl + render in the container).
- Public endpoints: rate limits, exact page matching (an empty URL used to match every fix).
- Brand: "OmniRank" was hard-coded in ~20 files; now only in `config/brand.json` (snippet is
  templated at serve time, SDK has neutral exports `getSeoMetadata` / `StructuredData`).
- `.env.example` inline comments were parsed as values (Phase 1 bug); fixed, tests ignore `.env`.

**Still open after the review** — items 1-5 were done on 2026-10-04 (see next section).
- WordPress plugin file/option names still hard-code the old "quardlink" slug.

## Real data + AI (2026-10-04)

- **Onboarding analysis**: real homepage fetch (SSRF-safe), platform fingerprint (shared
  `app_core.platform_detect`), page facts (`app_core.page_facts`), Claude identifies brand,
  industry, city, country, competitors; suggestions (~15 keywords + 30 questions per enabled
  language) written from the site. Clear notices when the site is unreachable, AI is off or the
  budget is used up. Live-tested on Allbirds (Shopify), wordpress.org, example.com.
- **AI answers**: ChatGPT (Responses API + web_search + location), Claude (SDK + web_search tool),
  Gemini (Interactions API + google_search), Perplexity (Agent API; Sonar was retired
  2026-09-27). Claude reads every answer (mention, position, other businesses, sentiment);
  citations matched on real hostnames; real costs.
- **Diagnosis agent**: Claude explains why competitors win and writes up to 5 page-specific
  fixes with platform steps; compares against pages that actually rank / get cited; no more
  placeholder pages; sanitized payloads; cost-guarded and logged.
- **Polish**: city-level rank tracking (DataForSEO city location codes), 149 hard-coded UI
  strings moved to `locales/en/ui.json`, FAQ fixes no longer add FAQPage schema or promise rich
  results (D2), raw i18n key + wrong copy labels on Integrations, plural on Admin, remaining
  "QuardLink" leftovers in API/connectors, content-block preview styling, IPv6 fetch fallback.
- `app_core.llm`: shared Claude client (official SDK, env-only models, structured output,
  refusal fallback, untrusted-content wrapping, per-call cost).

## Phase 7: Billing & payments (not started)

- Moyasar & Tap payment integrations for Saudi Arabia (SAR, mada, Apple Pay).
- Stripe integration for international payments.
- Subscription billing, webhooks, checkout flows, and self-serve plan upgrades.

## Pre-testing completion (2026-10-06)

- **Gemini runs the AI features** (D25): `LLM_PROVIDER=auto|gemini|anthropic`; Gemini via the
  Interactions API with JSON-schema output. With only a Gemini key everything works.
- **Cost alerts** at 80% / 100% are emailed to org owners/admins + `OPS_ALERT_EMAIL`, once per
  level per month (they only logged before).
- **Worker task registration**: audit and digest tasks were never registered, so "Run audit"
  and digests silently did nothing. Fixed + test that every enqueued task is registered.
- **Weekly digest** scheduled Mondays 08:00 UTC.
- **WordPress plugin**: the downloadable (generated) plugin now outputs safe JSON-LD once; the
  unused static copy with the old name was deleted.
- **Snippet tests** on static / SPA / Wix-like / Shopify-like pages (12 tests); fixed AI-referral
  beacons being rejected by the API (text/plain body).
- **API no longer runs worker code**: test digest is queued; reports require a finished audit;
  guard test prevents app_api importing app_worker.
- Tests: 190 pytest, 38 Vitest, 1 Playwright E2E — all passing.
