# Webflow

Sources (checked 2026-09-29):
- [Update Page Metadata](https://developers.webflow.com/data/reference/pages-and-components/pages/update-page-settings)
- [Custom Code guide](https://developers.webflow.com/data/docs/custom-code)

## Capabilities
- **Page SEO**: `PUT /v2/pages/{page_id}` sets title, slug, SEO title and
  description, and Open Graph fields. Scope `pages:write`. Optional `localeId`
  for Webflow Localization (secondary-locale slug changes need an
  Advanced/Enterprise localization add-on).
- **CMS items**: Data API can create/update items as drafts, the content-fix
  path for CMS-driven pages.
- **Custom Code API**: register inline (≤ 10,000 chars) or hosted scripts
  (URL + SRI hash), then apply them to the site or a page, head or footer.
  - **Only OAuth Webflow Apps** can use it (not site tokens). Scopes
    `custom_code:write` + `sites:write` / `pages:write`.
  - Changes go live only after **publish**. Webflow's guidance is to prompt the
    user to publish rather than auto-publish, which matches our "never
    auto-publish" rule.
  - Registered scripts are **JavaScript**. Raw `<script type="application/ld+json">`
    blocks are not documented as supported, so via API, JSON-LD gets injected by
    JS (client-side). Server-side JSON-LD needs a manual paste in page settings
    → Custom code, or a CMS rich-text/embed field. Verify in Phase 4.

## Delivery mapping
| Fix | Delivery |
|---|---|
| Meta | Data API page SEO fields (server-side) |
| Schema | Manual paste (server-side, recommended for AI) **or** registered script (client-side) |
| Content/FAQ | CMS item draft, or manual |

## Platform rules (audit)
- Webflow staging domain (`*.webflow.io`) indexable / not canonicalized.
- CMS template pages missing dynamic SEO bindings (identical titles).
- Missing alt text bindings on CMS images.
