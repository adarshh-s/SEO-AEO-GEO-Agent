# Salla (سلة)

Sources (checked 2026-09-29):
- [Salla Partners docs](https://docs.salla.dev/), [OAuth 2.0](https://docs.salla.dev/doc-421118), [Merchant API](https://docs.salla.dev/doc-426392)
- [Update Product](https://docs.salla.dev/5394170e0), [Update Category](https://docs.salla.dev/5394209e0), [List SEO settings](https://docs.salla.dev/5394262e0), [Update SEO settings](https://docs.salla.dev/5394263e0), [Merchant API changelog](https://docs.salla.dev/421127m0)
- [Device Mode / App Snippet](https://docs.salla.dev/1724504m0), [Create your first app](https://docs.salla.dev/421410m0)
- [Standards for publishing Salla apps](https://salla.dev/blog/standards-salla-apps-publications/), [Demo stores](https://salla.dev/blog/how-to-test-your-app-using-salla-demo-stores/)
- [Twilight themes](https://docs.salla.dev/doc-422053)

## Capabilities (better than expected)
- **OAuth 2.0 partner apps** with a Merchant API (REST, `api.salla.dev/admin/v2`).
- **Product SEO**: `metadata_title`, `metadata_description` (and `metadata.url`)
  on Create/Update Product, Update by SKU, and in product webhooks.
- **Category SEO**: `metadata_title`, `metadata_description`, `metadata_url`.
- **Store SEO settings**: `GET/PUT /admin/v2/seo` (title, keywords, description).
- **App Snippet**: the partner registers a hosted JS URL in the Partners Portal.
  Salla injects it into every storefront where the app is installed. This is
  how our `agent.js` would load, with no merchant paste needed. Per-store
  config (site key) comes from app settings / the install webhook (verify).
- Themes are server-rendered (Twilight, Twig), so native SEO fields are
  server-side.

## Constraints
- Apps must be **reviewed and published** (public or private type) before
  merchants can install them. Test on **demo stores** first.
- App Snippet JSON-LD is client-side (JS). For AI crawlers, prefer native
  metadata fields. Product JSON-LD is theme-generated; we can't write it
  server-side via API (verify whether Twilight exposes a hook).
- Arabic/English store variants: check product metadata per language (verify
  whether the API takes per-locale values).

## Launch plan (per decision #2)
- **Launch:** snippet via manual paste where the theme allows custom code, plus
  manual instructions (Salla dashboard → Products → SEO), in Arabic and English.
- **Full integration later** needs: Salla Partner account, app registration
  (OAuth scopes: products read/write, store settings/SEO), App Snippet
  registration, passing app review, and demo-store testing. Effort ≈ 1–2 weeks
  of dev plus review time.
