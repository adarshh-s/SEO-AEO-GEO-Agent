# Cloudflare edge worker

Sources: Cloudflare Workers [HTMLRewriter](https://developers.cloudflare.com/workers/runtime-apis/html-rewriter/) docs.
Stable API; re-verify limits and pricing in Phase 4.

## Design
- Template Worker on the customer's zone route (`example.com/*`). On HTML
  responses (`content-type: text/html`), HTMLRewriter:
  - `head` → append approved JSON-LD blocks, replace `<title>`, set/replace meta description and canonical;
  - optional content blocks into a configured selector.
- Fixes fetched from `GET /public/v1/fixes?site=KEY&url=...` and cached in the
  Workers Cache API (short TTL + purge webhook from our API). Fail-open: any
  error → pass the origin response through untouched.
- Logs AI crawler visits (matched by UA + verified IP ranges where the vendor
  publishes them) and AI referrals, batched to `POST /public/v1/events` via
  `ctx.waitUntil`.
- Deployment: "Deploy to Cloudflare" button / wrangler template; the customer
  owns the Worker. No Cloudflare OAuth needed at launch.
- Works for any platform proxied by Cloudflare, **except** where the platform
  controls DNS/SSL itself (Shopify, Wix, Squarespace, and Framer typically
  require their own DNS, so no orange-cloud proxy). Mostly useful for coded
  sites and self-hosted WordPress.
