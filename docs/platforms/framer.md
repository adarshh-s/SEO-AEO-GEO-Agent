# Framer

Sources (checked 2026-09-29):
- [How to add custom code](https://www.framer.com/help/articles/how-to-add-custom-code/)
- [Developers: Custom Code (plugin API)](https://www.framer.com/developers/custom-code)
- [Server API introduction](https://www.framer.com/developers/server-api-introduction), [Quick start](https://www.framer.com/developers/server-api-quick-start), [examples](https://github.com/framer/server-api-examples)
- [Make your site readable by AI agents](https://www.framer.com/help/articles/make-site-readable-by-ai-agents/)
- [Traffic-aware Pre-Rendering](https://www.framer.com/help/articles/dynamic-optimization/)

## Capabilities
- Site Settings → Custom Code (head start/end, body start/end), and page-level
  custom code. CMS pages can carry structured data.
- **Pre-rendered HTML**: Framer renders every page on its servers at publish.
  Crawlers that don't run JS get full text, title/meta, canonical, and JSON-LD
  placed in custom code. **So head custom code on Framer counts as server-side
  delivery.** The spec's "Framer = JS-heavy" assumption is outdated; the
  raw-vs-rendered diff will confirm per site.
- **Plugin API** `framer.setCustomCode({html, location})`, with locations
  `headStart | headEnd | bodyStart | bodyEnd`. Users can disable plugin-set code.
- **Server API** (`framer-api` npm package): a per-project API key created by
  the user authenticates as that user. It "shares the same capabilities as the
  Plugin API" and can update **and publish** projects. It may be able to set
  custom code and CMS items server-side. **Verify in Phase 4**: status
  (beta?), plan limits, whether `setCustomCode` and page SEO fields are
  available via Server API. Our "never auto-publish" rule means we'd save
  changes and ask the user to publish, or publish only on explicit click.

## Delivery mapping (proposed)
| Fix | Delivery |
|---|---|
| Meta | Manual (page settings), or Server API if it exposes page SEO |
| Schema | Server API custom code (if verified), else manual paste in page custom code |
| Content/FAQ | CMS item via Server API (draft), else manual |
| Snippet | Site Settings → Custom Code → head (one-time paste) |

## Platform rules (audit)
- `*.framer.app` / `*.framer.website` staging domain indexable.
- CMS page SEO bindings missing (identical titles).
- Custom code set but disabled by the user.
