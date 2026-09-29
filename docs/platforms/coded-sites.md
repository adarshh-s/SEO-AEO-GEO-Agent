# Coded / custom sites

Covers `nextjs`, `nuxt`, `astro`, `react_spa`, `vue_spa`, `static`, `custom_backend`.

## Detection signals (Phase 2)
| Platform | Signals |
|---|---|
| Next.js | `/_next/static/`, `__NEXT_DATA__` (pages router), `self.__next_f` (app router), `x-powered-by: Next.js` |
| Nuxt | `/_nuxt/`, `window.__NUXT__`, `data-n-head` / `nuxt-` attrs |
| Astro | `astro-island`, `/_astro/`, generator meta |
| React SPA | empty `#root` / `#app` in raw HTML + bundle only; no SSR markers |
| Vue SPA | `#app` shell + `data-v-` only after render |
| Static | no framework markers, content in raw HTML |
| Custom backend | `x-powered-by` (PHP, Express, ASP.NET), `laravel_session` / `csrftoken` cookies, `.aspx` / `.php` paths |

`rendering` = server / client / hybrid, decided from the raw-vs-rendered diff
(visible text ratio, headings, and links present only after JS).

## Delivery options
1. **`sdk-js`** (recommended for SSR frameworks): server-side fetch of approved
   fixes by URL, cached (stale-while-revalidate, ISR-friendly).
   - Next.js App Router: `export const generateMetadata = rankagent.metadata(...)`
     merges our title/description/canonical with the app's own values;
     `<RankAgentSchema url=... />` server component renders JSON-LD.
   - Nuxt: `useHead` composable module. Astro: component + integration.
   - Verify current Next.js `generateMetadata` / Metadata API docs in Phase 4.
2. **GitHub PR** (static / custom backends): a GitHub App (minimal scopes:
   contents + pull_requests on selected repos). We locate the template/page file
   for a URL (heuristics + user mapping) and open a PR with the change. Never
   merge ourselves.
3. **REST API + webhooks** for teams that want to integrate themselves.
4. **Snippet** fallback. For client-only SPAs, show the "AI crawlers won't see
   this" warning plus a prerender/SSR guide (e.g. Vite SSG, Next migration,
   prerender services).
5. **Cloudflare edge worker** if the site is behind Cloudflare.

## Platform rules (audit)
- SPA with empty raw HTML → the highest-severity AEO finding.
- Next.js: pages missing `generateMetadata`, `metadataBase` unset (relative OG
  URLs), client components holding main content.
- Soft 404s (200 status for unknown routes) in SPAs, hash routing.
