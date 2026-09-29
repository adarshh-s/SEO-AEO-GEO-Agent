# CLAUDE.md — RankAgent (working name, rename freely)

You are building **RankAgent**, a multi-tenant SaaS that helps businesses rank in
Google (SEO) and get mentioned/cited in AI answers (AEO/GEO: ChatGPT, Perplexity,
Gemini, Claude, Google AI Overviews). Businesses sign up, connect their website,
and the agent continuously **tracks → diagnoses → fixes → reports**.

It must work for **both kinds of websites**:
- **No-code / website-builder sites**: WordPress, Shopify, Wix, Webflow,
  Squarespace, Framer, and Saudi e-commerce platforms Salla and Zid.
- **Coded / custom sites**: static HTML, React/Vue SPAs, Next.js/Nuxt/Astro,
  and custom backends (PHP, Laravel, Django, Node, .NET, etc.).

**Language:** English is the primary and default language everywhere. Arabic is an
optional add-on that a user or a website can enable. It is never mandatory.

Read this whole file before writing code. Build in the phases listed at the end.
After each phase: run tests, summarize what you built, list open questions, and
STOP for my review before starting the next phase.

---

## 1. Product summary

Target customer: businesses (SMBs to mid-size companies), many in Saudi Arabia /
GCC, who are not SEO experts. The product must feel simple: "Here is your
visibility score, here is why competitors beat you, here are the fixes — approve
them and we apply them to your website, whatever it's built with."

Core loop per website:
1. **Track** Google rankings for target keywords (by country/city, mobile/desktop,
   in each language enabled for the site).
2. **Track** AI visibility: run customer-style prompts against multiple LLMs,
   detect brand mentions, website citations, position, sentiment, and the
   competitors mentioned instead.
3. **Diagnose** why the business is missing for a keyword/prompt by comparing its
   page against the pages that rank or get cited, using platform-aware checks.
4. **Fix**: generate concrete fixes (JSON-LD schema, meta titles/descriptions,
   answer-first content blocks, FAQ/Q&A sections, article briefs, listing
   opportunities, technical fixes) in the site's enabled languages. The user
   approves → the fix is deployed through the best integration for that platform,
   or given as copy-paste instructions.
5. **Report**: dashboard + weekly email + branded PDF showing trends and actions taken.

Never promise guaranteed rankings anywhere in UI copy. Frame everything as
"measure, diagnose, improve".

---

## 2. Language requirements

Build all of this into the architecture from Phase 1. Don't add it later.

**App interface language**
- Default UI language: **English**.
- Users can switch the interface to Arabic in settings or with a header toggle.
  The choice is saved per user.
- All user-facing strings go through `react-i18next` from day one. English is the
  source locale; Arabic translations live in separate files and may be incomplete
  (fall back to English for missing keys).
- RTL layout (`dir="rtl"`, mirrored layout via Tailwind logical properties) is
  applied **only** when the UI language is Arabic.
- Design the i18n system so more languages can be added later without code
  changes beyond adding a locale file.

**Website tracking languages (per site)**
- Every site has `primary_language` (default `en`) and optional
  `additional_languages[]` (e.g. `ar`). Arabic is opt-in during onboarding or later
  in site settings, never pre-selected.
- Keywords and AI prompts each carry a `language` field. Suggested keywords and
  prompts are generated only in the site's enabled languages.
- Brand-name matching supports multiple spellings per language (e.g. an English
  name plus an optional Arabic name), entered by the user.
- Generated fixes and content are produced in the language of the target page,
  detected from `<html lang>`, hreflang, or content. The user can override it.
- Reports and emails are generated in the recipient's chosen UI language, English
  by default.
- If a site has multiple languages, check hreflang correctness (reuse claude-seo's
  hreflang checks).

---

## 3. Tech stack (use these unless you have a strong reason; ask me first)

**Frontend** (`/apps/web`)
- React 18 + TypeScript + Vite
- React Router, TanStack Query, Zustand (light global state only)
- Tailwind CSS (logical properties for RTL) + shadcn/ui, Recharts, lucide-react
- react-i18next (English default, Arabic optional), react-hook-form + zod

**Backend API** (`/apps/api`)
- Python 3.11+, FastAPI, SQLAlchemy 2 + Alembic, Pydantic v2
- PostgreSQL 16, Redis
- Auth: email/password + Google sign-in, JWT access + refresh tokens (httpOnly cookies)

**Workers** (`/apps/worker`)
- Python, Celery (or arq) on Redis, with Celery Beat for schedules
- Playwright Chromium for rendering JavaScript-heavy sites (SPAs, Wix, Framer, etc.)
- Reuse the MIT-licensed `claude-seo` repo scripts (see section 9)

**Integration packages** (`/packages/*`)
- `snippet` — universal JS snippet (vanilla TS, esbuild, < 15 KB gzipped)
- `sdk-js` — npm package for coded sites (Node/Next.js/React helpers)
- `wp-plugin` — WordPress plugin (PHP)
- `shopify-app` — Shopify app (theme app extension + Admin API)
- `edge-worker` — Cloudflare Worker template for server-side injection
- Other platform connectors live in `/apps/api/integrations/<platform>/`

**Infra**
- `docker-compose.yml` for local dev: postgres, redis, api, worker, beat, web
- `.env.example` documenting every variable; never commit secrets
- Frontend deployable to Vercel/Netlify; API + workers as Docker containers
  (Railway / Render / Fly.io / VPS). Workers must NOT depend on serverless
  runtimes, because they run long jobs and Chromium.

---

## 4. External services (all keys via env vars)

| Purpose | Service | Env var |
|---|---|---|
| Reasoning, diagnosis, fix generation | Anthropic Claude API | `ANTHROPIC_API_KEY`, `CLAUDE_MODEL_MAIN`, `CLAUDE_MODEL_FAST` |
| AI visibility checks | OpenAI API (with web search) | `OPENAI_API_KEY` |
| AI visibility checks | Perplexity API | `PERPLEXITY_API_KEY` |
| AI visibility checks | Google Gemini API (search grounding) | `GEMINI_API_KEY` |
| AI visibility checks | Claude with web search tool | reuses `ANTHROPIC_API_KEY` |
| Google SERP rankings, AI Overview presence, keyword volume | DataForSEO | `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` |
| Page speed / Core Web Vitals | PageSpeed Insights + CrUX | `GOOGLE_API_KEY` |
| Search Console (per customer, OAuth) | Google OAuth | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` |
| Platform connectors | Shopify, Wix, Webflow, Salla, Zid, GitHub app credentials | `SHOPIFY_*`, `WIX_*`, `WEBFLOW_*`, `SALLA_*`, `ZID_*`, `GITHUB_APP_*` |
| Payments | Stripe + pluggable adapter (Moyasar/Tap for KSA later) | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` |
| Email | Resend or SMTP | `EMAIL_*` |
| File storage | S3-compatible | `S3_*` |

Model names must come from env config, never hard-coded. Use the fast model for
parsing, extraction, and classification, and the main model for diagnosis and content.

Wrap every provider behind an interface (`LLMProvider`, `SerpProvider`,
`PaymentProvider`, `PlatformConnector`) so each one can be swapped or mocked in tests.

---

## 5. Website platform detection & crawling (works for no-code AND coded sites)

**Auto-detect the platform** when a site is added, and let the user confirm or
override it. Detect from generator meta tags, CDN/asset hostnames, script globals,
response headers, and known URL patterns. Store `platform` (wordpress, shopify,
wix, webflow, squarespace, framer, salla, zid, nextjs, nuxt, react_spa, vue_spa,
astro, static, custom_backend, unknown) and `rendering` (server / client / hybrid).

**Crawling and auditing rules**
- Always fetch raw HTML **and**, when the site is client-rendered or the platform is
  JS-heavy (Wix, Framer, SPAs), a Playwright-rendered version. Compare them.
  Flag content that exists only after JavaScript runs, because many AI crawlers
  don't execute JS. This is one of our most valuable findings for coded SPA sites.
- Respect robots.txt and crawl politely (rate limits, a clear user agent).
- Check robots.txt rules for AI crawlers (GPTBot, OAI-SearchBot, PerplexityBot,
  ClaudeBot, Google-Extended, etc.) and report which are blocked, since blocking
  them affects AI visibility.

**Platform-specific audit checklists** (`/apps/worker/seo_engine/platform_rules/`)
- Each platform has a rules module with known issues and platform-correct fix
  instructions. Examples: Shopify duplicate collection/product URLs and default
  theme schema gaps; Wix and Framer JS-rendering and limited head control;
  Squarespace code-injection limits; WordPress plugin conflicts (existing SEO
  plugins like Yoast/Rank Math, which we detect and don't duplicate); Salla/Zid
  product schema and Arabic/English store variants; SPA missing SSR/prerendering;
  Next.js metadata API usage.
- Fix instructions must be written for that platform's UI ("In Wix: Settings →
  Custom Code → …") or code ("In Next.js App Router, add to `generateMetadata`…").
  Instructions are generated in the user's UI language.
- Research each platform's current capabilities and APIs before implementing its
  rules or connector. Platforms change often, so don't rely on memory. Document
  sources in `docs/platforms/<platform>.md`.

---

## 6. Website integration (the key product feature)

Build a guided **"Connect your website"** wizard. It shows the best options for
the detected platform first, with a clear label for each: *Automatic
(recommended)*, *One-time paste*, or *Manual*.

**Step 1 — Ownership verification** (required before any fix deployment)
- DNS TXT record, OR `<meta name="rankagent-verification">` tag, OR installed
  snippet/app/plugin, OR connected platform OAuth.

**Step 2 — Delivery method, by platform**

| Platform type | Primary method (recommended) | Fallback |
|---|---|---|
| WordPress | RankAgent WordPress plugin: server-side schema/meta, draft posts | Snippet in header, manual |
| Shopify | Shopify app: theme app extension for JSON-LD, Admin API for SEO title/description and metafields | Snippet via theme.liquid, manual |
| Wix | Wix connector via official APIs where available, else Custom Code (head) snippet | Manual instructions |
| Webflow | Webflow Data API for CMS items and page SEO fields; head custom code for schema | Manual |
| Squarespace | Header code injection (snippet + static JSON-LD) | Manual per-page instructions |
| Framer | Site settings custom code (snippet) | Manual |
| Salla / Zid | Partner app via their developer APIs, if capabilities allow (verify first) | Snippet if supported, manual |
| Next.js / Nuxt / Astro / SSR frameworks | `sdk-js` npm package: fetch approved fixes server-side at build or request time (e.g. helper for Next.js `generateMetadata` + a `<RankAgentSchema />` component) | REST API, snippet |
| React/Vue SPA (client-only) | Snippet + a strong recommendation and guide to add SSR/prerendering | `sdk-js`, REST API |
| Static HTML / custom backend | GitHub/GitLab integration: open pull requests with fixes, OR REST API + webhooks | Snippet, manual |
| Any site on Cloudflare | Edge worker template: injects approved fixes into HTML **server-side** using HTMLRewriter, and logs AI crawler visits | Any of the above |

**Universal JavaScript snippet** (works on every platform that allows head code)
```html
<script async src="https://cdn.<ourdomain>/agent.js" data-site="SITE_KEY"></script>
```
- Fetches approved fixes for the current URL from a cached, read-only public
  endpoint (`GET /public/v1/fixes?site=KEY&url=...`) and applies them: JSON-LD
  injection, title/meta/canonical updates (if enabled), content blocks inside a
  customer-defined container selector.
- Sends cookieless pageview pings (URL, referrer, whether the referrer is an AI
  engine such as chatgpt.com / perplexity.ai / gemini.google.com) for **AI referral
  traffic** reporting. No personal data; document this on the privacy page.
- Must never break the host site: try/catch everything, a single namespace, zero
  dependencies, fail silently, no layout shift.
- **Show this limitation honestly in the UI:** Google renders JavaScript, so
  snippet-injected schema/meta generally works for Google. Many AI crawlers do
  NOT run JavaScript, so for AI visibility, server-side delivery (plugin, app,
  SDK, edge worker, pull request, or manual paste) is preferred. Each fix shows
  its recommended delivery method for the site's platform.

**Always available for every site**
- Every fix has a "Copy code" view, a downloadable file, and step-by-step
  platform-specific instructions.
- Public REST API (API-key auth, scoped), webhooks (`fix.approved`,
  `fix.deployed`, `audit.completed`, `score.changed`), and a generated OpenAPI docs page.
- Google Search Console OAuth for clicks/impressions/queries (any platform).

**Deployment safety**
- Every deployment is reversible: keep the previous state, allow one-click
  rollback, and record who approved it in `audit_log`.
- Before deploying, check for existing schema/meta on the page (including from
  Yoast, Rank Math, Shopify themes, etc.) and merge or replace instead of
  duplicating.
- Never auto-publish content. Content goes out as drafts or requires an explicit
  publish click.

---

## 7. Data model (starting point — refine, but keep multi-tenancy strict)

- `organizations`, `users` (ui_language default `en`), `memberships` (owner/admin/member/viewer)
- `plans`, `subscriptions`, `usage_counters` (per org, per billing period)
- `sites` (org_id, domain, platform, rendering, primary_language default `en`, additional_languages[], verified_at, verification_method, site_key, default_country, brand_names jsonb {lang: [names]}, competitor_domains[])
- `keywords` (site_id, keyword, language, country, city, device, tags)
- `rank_checks` (keyword_id, checked_at, position, url_ranked, serp_features, ai_overview_present, ai_overview_cites_site)
- `ai_prompts` (site_id, prompt_text, language, country, intent, tags)
- `ai_checks` (prompt_id, engine, model, run_index, checked_at, raw_answer, brand_mentioned, mention_position, site_cited, cited_urls[], competitors_mentioned[], sentiment)
- `visibility_scores` (site_id, date, language, seo_score, ai_share_of_voice, per_engine jsonb)
- `crawl_snapshots` (site_id, url, raw_html_hash, rendered_html_hash, js_only_content_detected, fetched_at)
- `audits` (site_id, type, status, started_at, finished_at, score, report_json, pdf_url, language)
- `diagnoses` (site_id, target_type keyword|prompt, target_id, findings jsonb, competitor_pages jsonb)
- `fixes` (site_id, diagnosis_id, type schema|meta|content_block|faq|article_brief|listing|technical, target_url, language, payload jsonb, recommended_delivery, status draft|approved|deployed|rejected|rolled_back, deployed_via, deployed_at, previous_state jsonb)
- `integrations` (site_id, type snippet|wordpress|shopify|wix|webflow|salla|zid|sdk|github|edge_worker|gsc|webhook, config jsonb, encrypted_credentials, status, last_sync_at)
- `api_keys` (org_id, hashed_key, scopes, last_used_at), `webhooks` (org_id, url, events[], secret)
- `ai_referral_events` (site_id, url, referrer_engine, occurred_at) — aggregated daily
- `ai_crawler_hits` (site_id, bot, url, occurred_at) — from edge worker / server logs
- `jobs` (type, status, progress, error), `audit_log`

Every query must be scoped by `org_id`. Add a test proving one org cannot read
another org's data through any endpoint.

---

## 8. How AI visibility tracking must work

- Each prompt runs against each enabled engine, in the prompt's language. Use
  web-search/grounded modes where the provider supports them.
- Run each prompt **N times** (configurable, default 3) per cycle, because answers
  vary. Store every run. Scores are percentages across runs.
- Parse answers with the fast Claude model into structured JSON: brand mentioned
  (match against all brand-name spellings for that language, fuzzy), first-mention
  position, whether the site domain is among cited URLs, competitors mentioned,
  and sentiment.
- **AI Share of Voice** = brand mentions ÷ total brand + competitor mentions across
  runs, per engine, per language, and overall.
- Prompt suggestions: from the site's content, industry, and city, suggest ~30
  realistic customer prompts **in the primary language (English by default)**, plus
  more in Arabic only if Arabic is enabled. The user edits and approves them.
- Enforce plan quotas BEFORE calling any paid API. Queue with backoff. Log the
  cost of every call to `usage_counters`.

---

## 9. Reusing claude-seo (MIT licensed)

- Add https://github.com/AgriciDaniel/claude-seo as a git submodule or vendored
  copy in `/vendor/claude-seo`. Keep its LICENSE and add attribution in
  `THIRD_PARTY_NOTICES.md`. Do not use the "Claude SEO" name in our branding.
- First, read its README, `docs/ARCHITECTURE.md`, `skills/`, `agents/`, and
  `scripts/`. Write `docs/claude-seo-mapping.md` showing which scripts we call
  directly (rendering, content extraction, schema validation, PageSpeed/CrUX,
  hreflang, URL safety/SSRF, PDF generation) and which skill/agent files we adapt
  as system prompts for our diagnosis and fix-generation agents.
- Call their scripts through a thin adapter (`apps/worker/seo_engine/`) so we can
  pull upstream updates easily.
- Use their URL safety / SSRF protections for EVERY outbound fetch of a
  customer-supplied URL.

---

## 10. Frontend pages (React)

Public: landing, pricing, integrations page (logos + how each platform connects),
login/signup, privacy, terms. English by default, Arabic via the language toggle.

App:
- **Onboarding wizard**: enter website URL → auto-detect platform, brand, industry,
  city, page language(s), and competitors (all editable) → choose tracking
  languages (English preselected; "Add Arabic" optional) → review suggested
  keywords + AI prompts → connect website (platform-specific options) → choose plan.
- **Overview dashboard**: SEO visibility score, AI Share of Voice (overall, per
  engine, per language filter), trends, weekly wins/losses, AI referral traffic,
  fixes awaiting approval.
- **Keywords**: position, change, ranking URL, AI Overview presence, language
  filter; "Why am I not ranking?" → diagnosis.
- **AI Visibility**: prompt × engine grid, raw answers, competitor leaderboard,
  language filter; "Why am I not mentioned?" → diagnosis.
- **Diagnosis view**: side-by-side with competitor pages, plain-language findings,
  JS-only-content warnings, generated fixes.
- **Fixes**: inbox with preview/diff, Approve / Edit / Reject, recommended delivery
  method for this platform, deploy status, rollback, copy code + platform steps.
- **Audits**: full-site audit with progress (SSE or polling), report, PDF download.
- **Reports**: history, email schedule, report language, branded PDF.
- **Integrations**: platform connection status, snippet code, plugin/app install
  links, SDK install guide, GitHub connection, edge worker guide, GSC, API keys, webhooks.
- **Settings**: organization, team roles, billing & usage, interface language,
  site languages.

UX rules: simple and clean, mobile responsive, RTL correct only when Arabic is
selected, loading/empty/error states everywhere, tooltips for any SEO jargon.

---

## 11. Security & quality requirements

- Strict tenant isolation (tested). Rate limiting on auth and public endpoints.
- Encrypt third-party credentials and OAuth tokens at rest; request minimal
  OAuth scopes for each platform.
- Hash API keys and show them once.
- SSRF protection on all customer-URL fetches; block private IP ranges.
- Sanitize and validate every fix payload before serving it to a live site (no
  arbitrary script injection; JSON-LD must be valid JSON; HTML content blocks are
  allowlist-sanitized).
- Verify webhook signatures (Stripe, Shopify, Wix, etc.); make jobs idempotent.
- Tests: pytest (mock all external providers and platforms), Vitest + React Testing
  Library, a Playwright E2E happy path, and snippet tests against sample pages
  (static, SPA, and mock Wix/Shopify-like pages).
- ruff + black, ESLint + Prettier, CI workflow. Structured logging. Per-org cost tracking.

---

## 12. Plans & quotas (placeholder values — configurable in DB)

| Plan | Sites | Keywords | AI prompts | AI engines | Languages per site | Check frequency | Audits/mo |
|---|---|---|---|---|---|---|---|
| Starter | 1 | 50 | 25 | 2 | 1 (+Arabic add-on) | weekly | 2 |
| Growth | 3 | 250 | 100 | 4 | 2 | 2× weekly | 10 |
| Business | 10 | 1000 | 400 | 4 | 2+ | daily | 40 |

---

## 13. Build phases (stop and report after each)

**Phase 0 — Plan.** Read claude-seo, write `docs/architecture.md` and
`docs/claude-seo-mapping.md`, research platform APIs and write
`docs/platforms/*.md` (what each platform allows: head code, SEO fields API,
schema control, app/plugin model), propose the folder structure, and list any
decisions you need from me. No feature code yet.

**Phase 1 — Foundation.** Monorepo, docker-compose, auth, orgs/users/roles, sites,
migrations, React app shell, i18n with English default + optional Arabic + RTL,
layout, onboarding wizard UI with mocked data, CI, demo seed data.

**Phase 2 — Crawling & tracking.** Platform detection, raw vs rendered crawling,
AI crawler robots.txt checks, DataForSEO rank tracking, AI visibility tracking
across engines and languages, scoring, schedules, dashboard/keywords/AI visibility
pages, quotas, cost logging.

**Phase 3 — Diagnose & fix + universal integrations.** Platform-aware diagnosis
agent, fix generation (language-aware), fixes inbox with approval, verification,
universal JS snippet with AI referral tracking, copy-paste + platform instructions,
REST API + webhooks, rollback, audit_log.

**Phase 4 — Deep integrations.** WordPress plugin, Shopify app, `sdk-js` for
Next.js/React, GitHub pull-request integration, Cloudflare edge worker, Google
Search Console. Then Webflow and Wix connectors.

**Phase 5 — Audits, reports, regional platforms.** Full-site audits via claude-seo
scripts, PDF + email reports (EN default, AR optional), Salla and Zid connectors
(if their APIs support it, per Phase 0 research).

**Phase 6 — Billing & launch.** Stripe subscriptions + usage limits, payment
adapter, landing/pricing/integrations pages, admin panel (orgs, usage, API costs),
production Dockerfiles, deployment guide.

---

## 14. Working rules for you (Claude Code)

- Plan before coding each phase; keep a running `docs/progress.md`.
- Ask me before adding a paid service, changing the stack, or making a product
  decision not covered here.
- Verify every third-party platform API against its current official docs before
  building a connector.
- Make small, reviewable commits with clear messages.
- Mock all external APIs in tests. `SEED_DEMO=true` fills a demo org with
  realistic fake data (one no-code site, one coded site; English data, plus one
  site with Arabic enabled) so the UI can be demoed without API keys.
- Never commit secrets. Keep `.env.example` complete.

---

## 15. Confirmed decisions (from review)

1. **Branding is centralized.** "RankAgent" is a placeholder. Product name, brand
   slug, snippet JS namespace, verification meta tag name, WP plugin slug, npm/
   package names, CDN host and user agent all derive from ONE brand config
   (`config/brand.json` → generated for Python/TS/PHP). Never hard-code the name
   elsewhere. Renaming = one change + regenerate.
2. **Salla/Zid fallback.** If full partner-app integration is blocked (partner
   approval, no head/theme write access), launch with snippet + manual
   instructions. Document what a full integration would need.
3. **Job queue:** Celery + Celery Beat on Redis.
4. **Per-org monthly cost ceiling** on paid API calls (DataForSEO + all LLM
   providers), on top of plan quotas: alert org admins and the platform operator
   at 80%; pause non-essential scheduled checks at 100%; platform admins can raise
   the limit per org.
