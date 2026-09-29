# Squarespace

Sources (checked 2026-09-29):
- [Using code injection](https://support.squarespace.com/hc/en-us/articles/205815908-Using-code-injection)
- [Squarespace developers](https://developers.squarespace.com/)

## Capabilities
- **No API** for pages, SEO fields or code injection. Public APIs are Commerce
  only (products, inventory, orders, transactions, webhooks). Squarespace is
  moving OAuth app credentials to self-service
  (`account.squarespace.com/developer-apps`); the old form closes 2026-09-30.
- **Code Injection** (site-wide header/footer) requires a **Business plan or
  higher**. **Per-page header injection**: Pages → gear → Advanced → Page Header
  Code Injection.
- Per-page SEO title/description: Page settings → SEO tab (manual).

## Delivery mapping
| Fix | Delivery |
|---|---|
| Meta | Manual per-page instructions (SEO tab) |
| Schema | **Manual paste** of static JSON-LD into per-page header injection (server-side, recommended) or snippet (client-side) |
| Content/FAQ | Manual instructions |

The snippet is a *one-time paste* in site-wide header injection.

## Platform rules (audit)
- Personal plan → no code injection: detect and tell the user plainly.
- Default `?format=json` / `/s/` asset URLs, duplicate collection and tag pages.
- Built-in schema is minimal (LocalBusiness from business info), so check for duplicates when adding ours.
