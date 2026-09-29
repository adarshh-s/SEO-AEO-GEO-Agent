# Decisions

## Confirmed (2026-09-29)
| # | Decision |
|---|---|
| C1 | "RankAgent" is a placeholder. All naming comes from `config/brand.json` (architecture §3). |
| C2 | Salla/Zid: snippet + manual instructions is an acceptable launch fallback; full-integration requirements are documented in `docs/platforms/salla.md` / `zid.md`. |
| C3 | Celery + Celery Beat on Redis. |
| C4 | Per-org monthly $ ceiling on paid API calls: alert at 80% (org admins + operator), pause non-essential scheduled checks at 100%, platform admin can raise per org. |
| D1 | Neutral internal package names (`app_core`, `app_api`, `app_worker`); only `config/brand.json` holds the brand. |
| D2 | FAQ fixes are content blocks; `FAQPage` schema only when the user opts in. Never promise a FAQ rich result. |
| D3 | Direct provider APIs first. `AnswerEngine` interface designed so a DataForSEO LLM Scraper premium engine can be added later; not built now. |
| D4 | Competitor detection: DataForSEO first, LLM fallback. |
| D5 | uv workspace (Python) + pnpm workspace (JS); no Turborepo/Nx. |
| D6 | Postgres Row-Level Security as a second layer behind app-level `org_id` filtering. |
| D7 | At 100% of ceiling pause non-essential work (scheduled rank/AI checks, scheduled audits, suggestion generation); essential work continues until a hard stop at 120%. |
| D8 | Operator cost alerts go to `OPS_ALERT_EMAIL` = adarshs18400@gmail.com (env-configurable). |
| D9 | Arabic UI uses Western digits (123) by default. |
| D10 | Frontend on Vercel; API, workers, Postgres, Redis on Railway. Prod domains `app.quardlink.com`, `api.quardlink.com`, `cdn.quardlink.com` (not yet purchased). All domains come from env; localhost for local dev. |
| D11 | Sentry optional, enabled only when `SENTRY_DSN` is set. |
| D12 | Starter plan engines: ChatGPT (OpenAI) + Gemini. |
| D13 | Retention, configurable: raw AI answers 13 months, HTML snapshots 90 days, aggregates forever. |
| D14 | Per-plan cost ceilings set after measuring real costs in Phase 2 (placeholders until then). |
| D15 | Snippet content blocks off by default and render only inside a customer-placed container. Schema and meta injection stay on. |
| D16 | Shopify app backend on FastAPI (no Remix server); `packages/shopify-app` holds the theme app extension + thin embedded page. |
| D17 | Brand/company name **QuardLink** (test name; legal entity not registered). No registrations are assumed to exist; see `docs/registrations-checklist.md`. |
| D18 | Webflow schema: manual paste as primary (server-side), Custom Code API as the automatic client-side option, with the trade-off shown in the UI. *(Recommendation accepted by default; not explicitly answered.)* |
| D19 | Resend in production, SMTP adapter as an option, Mailpit locally. |
| D20 | **Payments deferred** to a final Phase 7. No payment code, checkout or billing webhooks until then. Plans assigned manually (new orgs → Trial plan with configurable limits; platform admin sets any org's plan). `PaymentProvider` interface + `subscriptions` table as placeholders only. Pricing page shows "Contact us". In Phase 7: Moyasar or Tap first (SAR, mada, Apple Pay), Stripe second. |

## Open
None blocking. New questions will be added here per phase.

## For your information (changes to spec assumptions, no action needed unless you disagree)
- **Framer and Wix serve pre-rendered HTML** to crawlers. We won't label them
  "JS-heavy" by platform; the raw-vs-rendered diff decides per page.
- **claude-seo has no hreflang script** (only an LLM skill). We'll write a
  deterministic validator following its 8 rules.
- **claude-seo's SSRF guard is process-global / not thread-safe**, so all
  customer-URL fetching runs in prefork Celery workers, never in the API.
- **Upstream `seo-flow` is CC BY 4.0**, not MIT. We don't adapt it.
- **WordPress.org guideline 8** forbids loading our JS from a CDN. The WP plugin
  renders fixes server-side (better for AI anyway) and logs referrals/bots in PHP.
- **Theme app extensions need Online Store 2.0 themes.** Vintage Shopify themes
  get manual/snippet fallback.
