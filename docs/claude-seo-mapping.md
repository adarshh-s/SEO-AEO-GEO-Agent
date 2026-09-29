# claude-seo → RankAgent mapping

Upstream: https://github.com/AgriciDaniel/claude-seo (MIT). Vendored as a git
submodule at `vendor/claude-seo`, pinned to `ff87fce` (v2.4.1, 2026-09-29).
We never edit files inside the submodule. Anything we change lives in our
adapter (`apps/worker/seo_engine/`) or in our own prompt files.

## 1. How claude-seo is built (what matters to us)

- It is a **Claude Code plugin**: 26 skills (`skills/*/SKILL.md`) and 19 agents
  (`agents/*.md`) are Markdown prompts. 60 Python scripts in `scripts/` do the
  deterministic work (fetching, rendering, parsing, API calls, reports).
- The scripts are **importable modules**, not only CLIs. Each exposes plain
  functions (for example `render_page(url, mode=..., user_agent=...) -> dict`)
  and has an argparse `main()` on top. They find each other by putting
  `scripts/` on `sys.path` and importing by bare module name
  (`from url_safety import ...`).
- `scripts/runtime.py` + `scripts/claude-seo` are a launcher that builds a
  private venv. **We don't use them.** Our worker image installs the same
  dependencies from `requirements.txt` itself.
- Python ≥ 3.10. Dependencies: requests, beautifulsoup4, lxml, playwright,
  trafilatura, htmldate, weasyprint, matplotlib, google-api-python-client and
  others. All are compatible with our Python 3.11 worker.

## 2. Integration approach

**In-process import through a thin adapter**, not subprocess calls:

```
apps/worker/seo_engine/
  _vendor_path.py      # puts vendor/claude-seo/scripts on sys.path (only here)
  fetch.py             # wraps fetch_page / url_safety → our FetchResult model
  render.py            # wraps render_page → RenderResult (raw + rendered + diff)
  parse.py             # wraps parse_html → PageFacts
  schema.py            # JSON-LD extraction / validation / generation
  performance.py       # pagespeed_check + crux_history + lcp_subparts
  robots_ai.py         # agentic_check robots/llms.txt pieces → AiCrawlerAccess
  content.py           # content_quality, metadata_template
  sitemap.py           # sitemap_discovery
  hreflang.py          # OUR validator (upstream has no script; see §4)
  report_pdf.py        # our templates; borrows google_report's WeasyPrint approach
  platform_rules/      # ours (not upstream)
```

Rules for the adapter:
1. Only the adapter imports vendor modules. The rest of our code depends on our
   own typed result models (Pydantic), so an upstream change breaks one file.
2. Every call passes **our** user agent (`BRAND.crawler_user_agent`). Upstream's
   default UA contains `ClaudeSEO`, which we must not send (branding, and it
   makes our traffic look like someone else's).
3. A contract test suite (`apps/worker/tests/seo_engine/test_vendor_contract.py`)
   runs the adapter against fixture HTML, so a submodule bump that changes
   result shapes fails CI.
4. Upstream bump procedure: `git -C vendor/claude-seo fetch && checkout <tag>`,
   run contract tests, update the pin in this doc.

### Critical constraint: `url_safety` is process-global

`url_safety._pin_dns` works by **monkey-patching `socket.getaddrinfo` for the
whole process** and guards it with a non-blocking lock. A second concurrent
pinned fetch in the same process raises
`URLSafetyError("... not thread-safe by design")`.

Consequences for our architecture:
- **Customer-URL fetches only happen in Celery workers using the `prefork` pool**
  (one task per process at a time). Never in FastAPI request handlers, and never
  with thread, gevent or eventlet pools.
- Throughput comes from more worker processes, not threads.
- The API asks for a fetch (for example platform detection during onboarding)
  by enqueueing a task and waiting on the result for ≤ 20 s, or by polling.
- Playwright uses the sync API (`sync_playwright`), which fits prefork.
- The browser route handler `make_safe_playwright_route_handler()` is attached
  to every Playwright page, so subresource requests are SSRF-checked too.

## 3. Scripts we call directly

| Our need (spec) | Upstream script → function | Notes |
|---|---|---|
| **URL safety / SSRF** (every customer URL) | `url_safety.validate_url_strict`, `safe_requests_get/head`, `safe_requests_session`, `make_safe_playwright_route_handler` | DNS-rebinding safe, blocks private/reserved/metadata IPs and authority confusion. Process-global; see above. |
| Raw HTML fetch | `fetch_page.fetch_page(url, user_agent=...)` | Returns status, headers, redirect chain, and content. |
| **Raw vs rendered** crawl | `render_page.render_page(url, mode="always", user_agent=...)` | Returns `raw_content` **and** `content` (post-JS DOM), `is_spa`, `extracted_text` (trafilatura), `publication_date`, console errors. The basis for our JS-only-content finding. We compute the diff ourselves (text blocks, headings, links, and JSON-LD present only after render). |
| Content extraction | `render_page` (trafilatura) + `parse_html.parse_html(html, base_url)` | parse_html gives title, meta, headings, links, images, canonical, hreflang links, OG, and JSON-LD blocks. |
| **Schema detection / validation** | `render_page._extract_json_ld` (private, so wrapped defensively), `schema_ecommerce_validate` for Product | Upstream has no general Schema.org validator. We add our own checks: valid JSON, `@context`, and required/recommended properties per type from `skills/seo/references/schema-types.md`, plus a deprecated-types list. |
| Schema generation (a few types) | `schema_generate` (Reservation, OrderAction, DiscussionForumPosting, ProfilePage) | Most of our schema fixes are LLM-generated and then validated. These helpers cover niche types. |
| **PageSpeed / CrUX** | `pagespeed_check.run_pagespeed`, `query_crux`, `combined_check`; `crux_history.query_history`, `detect_trends`; `lcp_subparts` | Uses `GOOGLE_API_KEY`. `google_auth.get_api_key` reads from upstream's config file; we inject the key via env through a small shim. |
| **AI crawler robots.txt** | `agentic_check.parse_robots`, `select_group`, `is_allowed`, `audit_robots`, `audit_llms` | RFC 9309 group selection. Bot table includes GPTBot, OAI-SearchBot, ClaudeBot, Claude-SearchBot, PerplexityBot, Google-Extended, Applebot-Extended and more. `audit_ua_matrix` tells us whether a CDN/WAF blocks AI user agents even when robots.txt allows them, which is a valuable finding. |
| Agent readiness (optional, later) | `agentic_check.audit`, `agent_ux_check`, `agentic_fix` | llms.txt, markdown negotiation, and similar. Nice to have for the AEO score. |
| Sitemaps | `sitemap_discovery` | Seeds the full-site audit crawl. |
| Content quality | `content_quality.analyse(text)`, `metadata_template` (templated titles) | Used by diagnosis. `content_quality` supports CJK detection; we must test it on Arabic text. |
| Drift | `drift_baseline` / `drift_compare` | Idea reused; their storage is SQLite, ours is Postgres `crawl_snapshots`. We reuse the comparison rules (`skills/seo-drift/references/comparison-rules.md`), not the storage. |
| **PDF generation** | Approach from `google_report.py` (HTML + CSS → WeasyPrint, matplotlib charts) | We don't call google_report directly: its layout and branding are theirs, and it is English-only. We build our own Jinja templates (EN/AR, RTL) rendered with WeasyPrint. WeasyPrint handles Arabic shaping and RTL but needs an Arabic font (Noto Naskh / IBM Plex Sans Arabic) in the image. |
| DataForSEO | `dataforseo_normalize`, `dataforseo_costs` | Useful references for response normalization and cost estimates. Our `SerpProvider` calls the DataForSEO REST API directly (upstream goes through the MCP server). |
| GSC | `gsc_query`, `gsc_inspect` | Reference only. We use per-customer OAuth tokens, while upstream uses a local service-account/OAuth file. We'll port the query and pagination logic. |

Not used: runtime/launcher, release signing, consistency_check, portability_check,
installers, banana/image-gen, Moz/Bing/Common Crawl/Matomo/GA4/Keywords
Everywhere/YouTube clients (they may come later, but none is in scope now).

## 4. Hreflang: no upstream script

The spec says "reuse claude-seo's hreflang checks". Upstream implements hreflang
**only as an LLM skill** (`skills/seo-hreflang/SKILL.md`, 8 validation rules
plus references on locale formats and content parity). There is no deterministic
script. Plan: implement `seo_engine/hreflang.py` ourselves as deterministic code
following the skill's 8 rules (self-reference, return tags, x-default, ISO 639-1
language codes, ISO 3166-1 region codes, canonical alignment, protocol
consistency, cross-domain), and use the skill text as a system prompt only for
the fuzzy parts (content parity and cultural adaptation for EN↔AR pages).

## 5. Skills / agents adapted as system prompts

Upstream prompts are written for Claude Code (they tell the model to use
`Bash`, `Read`, `WebFetch` and to call the launcher). We **adapt** them: strip
tool/launcher instructions, keep the domain rules and quality gates, add our
JSON output schema, language instructions and platform context. Adapted copies
live in `apps/worker/agents/prompts/<name>.md`, each with a header naming its
upstream source file and commit.

| Our agent / task | Model | Upstream sources adapted |
|---|---|---|
| **Diagnosis agent** (why page X isn't ranking or cited vs competitor pages) | main | `agents/seo-technical.md`, `agents/seo-content.md`, `agents/seo-geo.md`, `skills/seo-page/SKILL.md`, `skills/seo/references/eeat-framework.md`, `quality-gates.md`, `thinking-framework*.md` |
| **AI visibility / GEO findings** | main | `skills/seo-geo/SKILL.md` + `references/google-ai-optimization-guide.md`, `llmstxt-evidence.md`; `skills/seo-agentic/references/access-policy.md`, `vendor-matrix.md` |
| **Schema fix generator** | main | `agents/seo-schema.md`, `skills/seo-schema/SKILL.md` (type status as of Jun 2026), `skills/seo/references/schema-types.md`, `local-schema-types.md`, `skills/seo-schema/references/deprecated-types-2024-2026.md` |
| **Meta title/description fixes** | main | `skills/seo-page/SKILL.md` (on-page rules), `metadata_template.py` heuristics |
| **Answer-first content blocks / FAQ** | main | `skills/seo-geo/SKILL.md` (citability, passage structure), `agents/seo-content.md` |
| **Article brief** | main | `skills/seo-content-brief/SKILL.md` + `references/page-type-templates.md`, `keyword-density.md` |
| **E-commerce (Shopify/Salla/Zid)** | main | `skills/seo-ecommerce/SKILL.md`, `agents/seo-ecommerce.md` |
| **Local businesses** (most KSA SMB customers) | main | `skills/seo-local/SKILL.md`, `agents/seo-local.md`, `skills/seo/references/local-*.md` |
| **Hreflang parity (EN↔AR)** | main | `skills/seo-hreflang/SKILL.md` + `references/content-parity.md`, `cultural-profiles.md`, `machine-translation-qa.md` |
| **Technical audit summary** | fast | `agents/seo-technical.md`, `skills/seo-technical/SKILL.md` |
| **Prompt/keyword suggestion** | fast | `skills/seo-plan/SKILL.md` (industry templates), `skills/seo-cluster/SKILL.md` |
| **Answer parsing (AI checks)** | fast | none upstream; ours. |

**Untrusted-content handling.** Competitor pages and LLM answers are untrusted
input to our agents (prompt injection risk). Upstream already has a pattern and
tests for this (`tests/test_agent_untrusted_content.py`). We copy the pattern:
wrap fetched content in delimited blocks, instruct the model to treat it as
data, and validate every model output against a Pydantic schema before storing
it.

**Not adapted:** `skills/seo-flow` (FLOW framework content is **CC BY 4.0**,
not MIT, so it would need separate attribution; skipped), image-gen,
backlinks, maps (depend on paid MCP data we don't have).

## 6. Content currency notes from upstream (affects our fixes)

- **FAQPage rich results were removed for all sites on 2026-05-07** (upstream
  README, schema skill). FAQ blocks still help AI answer extraction, but our UI
  must not promise a Google FAQ rich result. HowTo is deprecated too. We'll
  maintain a deprecated-types list sourced from upstream.
- INP replaced FID. Never report FID.
- Google-Extended is shared with Gemini and renders JS. GPTBot, ClaudeBot and
  PerplexityBot don't execute JS (upstream `seo-geo` + our research).

## 7. Attribution

`THIRD_PARTY_NOTICES.md` carries the MIT notice. Adapted prompt files keep a
header: `Adapted from claude-seo (MIT) <path>@<commit>`. Our product never uses
the "Claude SEO" name.
