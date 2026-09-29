# Platform capability matrix

Researched 2026-09-29 from official docs (links in each file). Platforms change
often. **Re-verify each connector against current docs at the start of the
phase that builds it** (CLAUDE.md §14).

Legend: ✅ supported · ⚠️ supported with caveats · ❌ not available · ❓ unverified

| Platform | Head code (manual) | Head/script via API or app | Per-page SEO title/desc via API | JSON-LD delivered **server-side** | App/plugin model | Review needed to ship |
|---|---|---|---|---|---|---|
| [WordPress](wordpress.md) | ✅ (theme / plugin) | ✅ our plugin (PHP hooks) | ✅ plugin (or Yoast/Rank Math fields) | ✅ plugin outputs in `wp_head` | wp.org plugin or direct zip | wp.org review (optional, zip works) |
| [Shopify](shopify.md) | ✅ theme.liquid edit | ✅ theme app extension **app embed** (`head` target, merchant must toggle; deep-link) | ✅ GraphQL `productUpdate.seo`, collections, pages, articles | ✅ Liquid in app embed reads app metafields | Shopify app (OAuth) | App Store review for public listing; custom/unlisted distribution possible |
| [Wix](wix.md) | ✅ Settings → Custom Code | ✅ Embedded Script API (head) | ✅ Item SEO Tags API (static pages, blog, store items) | ✅ via Item SEO Tags (structured-data tag, verify) | Wix app (OAuth) | Wix App Market review |
| [Webflow](webflow.md) | ✅ site/page custom code | ⚠️ Custom Code API (JS only, 10k char inline, app OAuth only, needs publish) | ✅ `PUT /v2/pages/{id}` (+ `localeId`) | ⚠️ JSON-LD via API only as JS (client-side); server-side needs Designer paste or CMS embed field | Webflow App (OAuth) | Marketplace review for listing |
| [Squarespace](squarespace.md) | ✅ Business plan+ (site + per-page header) | ❌ no pages/SEO/code API | ❌ | ⚠️ only via manual paste into Code Injection | Commerce APIs only | n/a |
| [Framer](framer.md) | ✅ site + page custom code | ⚠️ Plugin API `setCustomCode`; Server API (API-key per project) shares plugin capabilities | ❓ via Server API (verify) | ✅ Framer pre-renders HTML, so head code is in the served HTML | Plugin / Server API key | Marketplace review for plugins; Server API key = none |
| [Salla](salla.md) | ⚠️ theme-dependent | ✅ App Snippet (hosted JS injected in storefront) | ✅ product/category `metadata_title/description`, store SEO settings | ⚠️ server-side only via Salla's own product/store SEO fields; JSON-LD via snippet = client-side | Partner app (OAuth) | **Yes**: app review and publishing (public or private) |
| [Zid](zid.md) | ⚠️ theme-dependent | ✅ App Scripts (JS/CSS snippet, placement configurable) | ✅ product SEO title/description, category SEO | ⚠️ same as Salla | Partner app (OAuth) | **Yes**: snippets are submitted for review |
| [Coded sites](coded-sites.md) | ✅ | ✅ `sdk-js`, REST API, GitHub PRs | ✅ via SDK / PR | ✅ SDK (SSR), PR, edge worker | npm / GitHub App | none (GitHub App is ours) |
| [Cloudflare edge](cloudflare.md) | n/a | ✅ Worker + HTMLRewriter | ✅ rewrite `<title>`/meta | ✅ | Customer deploys Worker (template / Deploy button) | none |
| [Google Search Console](google-search-console.md) | n/a | n/a | n/a | n/a | Google OAuth | Google OAuth verification (sensitive scope) |

## Cross-cutting findings that change the spec's assumptions

1. **Framer is not "JS-only".** Framer pre-renders every page to HTML on its
   servers, including head custom code and JSON-LD. Crawlers that don't run JS
   still see the content. Wix also serves server-rendered HTML to bots.
   → Don't hard-code "Wix/Framer = JS-heavy". The raw-vs-rendered diff decides,
   per page. The platform only sets the *default* for whether we render.
2. **Snippet-injected changes are client-side everywhere.** On every platform
   where our only delivery is a JS snippet (Squarespace, Framer via snippet,
   Salla/Zid snippets, Webflow custom code API), AI crawlers that don't run JS
   won't see the injected JSON-LD/meta. The server-side paths per platform are:
   WP plugin, Shopify app embed, Wix Item SEO Tags, Salla/Zid native SEO fields,
   Webflow page SEO fields, Framer custom code (pre-rendered), SDK, PR, and edge
   worker. The "recommended delivery" logic encodes this per fix *type* (meta vs
   schema vs content block), not only per platform.
3. **Body content edits are rarely possible via API.** Wix has no API for
   editing placed page body copy. Squarespace has none. Webflow can only edit
   CMS items. So "content block" and "FAQ" fixes on builders default to
   **manual paste with instructions**, or to CMS/blog drafts where an API exists
   (WP drafts, Shopify/Wix blog drafts, Webflow CMS items as drafts).
