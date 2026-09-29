# Zid (زد)

Sources (checked 2026-09-29):
- [Start here](https://docs.zid.sa/start-here), [Overview](https://docs.zid.sa/)
- [App Scripts](https://docs.zid.sa/app-scripts-649611m0)
- [Update Product](https://docs.zid.sa/update-an-existing-product), [Products](https://docs.zid.sa/products), [List Categories](https://docs.zid.sa/get-all-categories)
- [Theme development](https://docs.zid.sa/theme-development), [Zid SDKs](https://docs.zid.sa/zid-sdks-2008123m0)
- Partner dashboard: https://partner.zid.sa

## Capabilities
- Partner apps with a Merchant API (orders, products, inventories, marketing,
  store settings, webhooks, app scripts).
- **Product SEO**: SEO title, SEO description and keywords on product
  create/update. **Categories** carry SEO info.
- **App Scripts**: JS or CSS snippets defined in the Partner Dashboard (app
  General Settings → Add Snippet), with configurable placement, global scripts,
  and event-driven scripts. **Changes are submitted for review and approval.**
- Themes: Jinja templates, server-rendered.

## Constraints
- App script review → our snippet loader must be generic and stable (load
  `agent.js` + site key) so we don't need re-review for every change.
- App Script JSON-LD is client-side. Prefer native product SEO fields for AI crawlers.
- OAuth details and app publication requirements weren't documented in the
  pages reviewed. Verify with Zid partner support.

## Launch plan (per decision #2)
- **Launch:** manual snippet paste (if the merchant's theme or plan allows
  custom code; verify) and manual SEO-field instructions (AR/EN).
- **Full integration later** needs: Zid partner account, app with product/
  category write scopes, App Script submission and review, dev-store testing.
