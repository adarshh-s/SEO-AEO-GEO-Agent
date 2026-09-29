# Shopify

Sources (checked 2026-09-29):
- [Theme app extensions](https://shopify.dev/docs/apps/build/online-store/theme-app-extensions)
- [Theme app extension configuration](https://shopify.dev/docs/apps/build/online-store/theme-app-extensions/configuration)
- [productUpdate (GraphQL Admin)](https://shopify.dev/docs/api/admin-graphql/latest/mutations/productUpdate)
- [App Store requirements](https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements)

## Capabilities
- **GraphQL Admin API only** for new public apps (required since 2025-04-01; REST is legacy).
- SEO title/description: `productUpdate(input: {seo: {title, description}})`,
  plus the equivalent for collections, pages and articles (verify each object's
  `seo` input in Phase 4).
- **App embed blocks** (theme app extension): targets `head`, `compliance_head`,
  `body`. Liquid can read **app-owned metafields** (`app.metafields.ns.key`), so
  we write JSON-LD to a metafield via the Admin API and the embed prints it
  server-side in `<head>`. This is the best path for AI crawlers.
  - Deactivated by default after install. The merchant must enable it, and we
    can **deep-link** (`/admin/themes/current/editor?context=apps&activateAppId={api_key}/{handle}`).
  - Limits: 10 MB total per extension, 30 blocks, 100 KB Liquid.
  - **Online Store 2.0 themes only.** Vintage themes → fallback: manual
    theme.liquid paste instructions, or our snippet.
- Blog articles can be created unpublished (`isPublished: false`), which gives
  content fixes a draft workflow.
- Mandatory compliance webhooks (customers/data_request, customers/redact,
  shop/redact) and HMAC verification for all webhooks.

## Delivery mapping
| Fix type | Delivery |
|---|---|
| Meta title/description | Admin API `seo` fields (server-side, native) |
| JSON-LD schema | App metafield + app embed (server-side). Merge with theme's own Product schema (Dawn etc. already output Product JSON-LD) to avoid duplicates. |
| Content block / FAQ | Manual instructions, or unpublished blog article |
| Technical | Instructions (e.g. theme edits) |

## Platform rules (audit)
- Duplicate product URLs: `/collections/x/products/y` vs `/products/y`
  (canonical handles it, but internal links in themes often point to collection paths).
- Theme default schema gaps (missing `brand`, `gtin`, `aggregateRating`,
  `shippingDetails`, `hasMerchantReturnPolicy`); reuse upstream `schema_ecommerce_validate`.
- `/collections/all`, tag-filtered collection URLs, and `?variant=` duplicates.
- Multiple markets/languages: Shopify Markets subfolders + hreflang (check with our hreflang validator).

## Open (verify in Phase 4)
- App review expectations for an SEO app that writes metafields and seo fields.
- Whether we need `write_themes` (avoid it; the app embed doesn't need it).
