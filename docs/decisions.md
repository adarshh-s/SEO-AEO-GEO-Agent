# Decisions

## Confirmed (2026-09-29)
| # | Decision |
|---|---|
| C1 | "RankAgent" is a placeholder. All naming comes from `config/brand.json` (architecture §3). |
| C2 | Salla/Zid: snippet + manual instructions is an acceptable launch fallback; full-integration requirements are documented in `docs/platforms/salla.md` / `zid.md`. |
| C3 | Celery + Celery Beat on Redis. |
| C4 | Per-org monthly $ ceiling on paid API calls: alert at 80% (org admins + operator), pause non-essential scheduled checks at 100%, platform admin can raise per org. |

## Open: needed before Phase 1
| # | Question | Recommendation |
|---|---|---|
| D1 | **Internal naming.** Use neutral internal Python package names (`app_api`, `app_worker`, `app_core`) so only `brand.json` carries the brand? | Yes. |
| D5 | **Tooling:** `uv` workspace for Python, `pnpm` workspace for JS, no Turborepo/Nx? | Yes. It's simple and fast, and we can add Turbo later if builds get slow. |
| D6 | **Postgres Row-Level Security** as a second tenancy layer on top of app-level `org_id` filtering? | Yes. It's cheap to add in Phase 1 and hard to retrofit. |
| D8 | **Operator alert address** for 80%/100% cost alerts and other "notify me" events (`OPS_ALERT_EMAIL`). Which email? | Your email, set via env. |
| D9 | Arabic UI: Western digits (123) or Arabic-Indic (١٢٣)? | Western digits by default (common in KSA business software); per-user option later. |
| D10 | **Deploy target** for API/workers, and a custom domain. Cookie auth across Vercel + API needs both on one parent domain (`app.x.com` + `api.x.com`). | Pick one host now (Railway or Fly.io) so docker-compose mirrors it; buy the domain before Phase 4 (Google OAuth verification needs it). |

## Open: needed before Phase 2
| # | Question | Recommendation |
|---|---|---|
| D2 | **FAQ fixes.** Google removed FAQ rich results for all sites on 2026-05-07. Keep "FAQ / Q&A block" as a *content* fix for AI answers but stop emitting `FAQPage` schema by default? | Yes. Emit FAQPage only if the user opts in, and never promise a rich result. |
| D3 | **AI visibility data source.** The spec says call OpenAI/Perplexity/Gemini/Claude APIs directly. API answers can differ from what users see in the consumer ChatGPT/Gemini apps. DataForSEO also offers **LLM Responses** (API passthrough, base $0.0006 + tokens) and an **LLM Scraper** (answers scraped from the consumer UI). Add DataForSEO LLM Scraper as an optional "consumer ChatGPT" engine? *(paid service → needs your OK)* | Build direct APIs first (spec). Add the DataForSEO LLM Scraper engine in Phase 2 behind a flag if you approve the spend. |
| D4 | **Competitor auto-detect** in onboarding: DataForSEO "competitors" data (paid, accurate) or LLM guess from site content (cheap, weaker)? | DataForSEO SERP overlap on 5–10 seed keywords, with LLM as fallback. |
| D7 | **Essential vs non-essential** at 100% ceiling. Proposed: *paused* = scheduled rank/AI checks, scheduled audits, suggestion generation; *still allowed* = user-clicked diagnosis/fix generation, onboarding detection, deploy/rollback, with a hard stop at 120% of the ceiling. OK? | Yes. |
| D11 | **Error monitoring**: Sentry (free tier is fine at first, but it's a paid service at scale)? | Yes, optional via `SENTRY_DSN`. |
| D12 | **Starter plan's 2 AI engines**: which two? | ChatGPT (OpenAI) + Gemini. Google AI Overviews come from SERP data on all plans. |
| D13 | **Data retention.** Raw AI answers and HTML snapshots are big. | Raw answers 13 months, HTML snapshots 90 days in S3, aggregates kept forever. |
| D14 | **Default ceilings per plan** (placeholder): Starter $15/mo, Growth $60/mo, Business $200/mo of raw API cost? | Set after a Phase 2 cost measurement on demo data; placeholders until then. |

## Open: needed before Phase 3–4 (flagging now because of lead time)
| # | Question | Recommendation |
|---|---|---|
| D15 | **Snippet content blocks vs "no layout shift".** Injecting content with JS always shifts layout unless the customer reserves space. | Content blocks via snippet off by default. When enabled, they render only into a customer-placed container (and we tell them to size it). |
| D16 | **Shopify app architecture.** Shopify's template is a Remix/Node app. Alternative: FastAPI handles OAuth + Admin GraphQL, and `packages/shopify-app` holds only the theme app extension + a thin embedded page (App Bridge) served from our web app. Avoids a second backend stack. | FastAPI-based. Verify App Store embedded-app requirements in Phase 4. |
| D17 | **Start partner/verification paperwork early** (weeks of lead time): Google OAuth verification (Search Console scope), Shopify Partner, Wix/Webflow app registration, Salla/Zid partner accounts. Who owns the accounts (company legal entity)? | Register accounts now under the company entity; I'll write step lists. |
| D18 | **Webflow schema delivery**: manual paste (server-side, best for AI) as primary, and the Custom Code API (client-side JS) as the automatic option? | Yes, and show the trade-off label in the UI. |
| D19 | **Email provider**: Resend (paid past free tier) or plain SMTP? | Resend in prod, Mailpit locally, SMTP adapter available. |
| D20 | **Payments region**: Stripe in USD first; Moyasar/Tap (SAR, mada) at launch or after? Affects Phase 6 only. | Stripe USD first, KSA adapter post-launch unless KSA customers need mada at launch. |

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
