# Wix

Sources (checked 2026-09-29):
- [Embedded Scripts API](https://dev.wix.com/docs/rest/app-management/embedded-scripts/introduction)
- [Item SEO Tags API: sample flows](https://dev.wix.com/docs/api-reference/business-management/seo/item-seo-tags-v1/sample-flows)
- [SEO Tags API intro](https://dev.wix.com/docs/api-reference/site/viewer/seo-tags/introduction)
- [wix/skills PR #741](https://github.com/wix/skills/pull/741) (documents API gaps)
- Wix dev docs expose LLM-friendly markdown: append `.md`, index at `https://dev.wix.com/docs/llms.txt`

## Capabilities
- **SEO APIs** (Site SEO Tags, SEO Patterns, **Item SEO Tags**): read/write
  titles, descriptions, social tags, canonical, structured data, and robots
  directives. Item types include `STATIC_PAGE`, blog posts and store products.
  - `Set Item SEO Tags` **replaces the full tag array**: read first, then write.
    `Bulk Set` accepts 100 items per call and is idempotent.
  - `publish: true` writes the live revision.
  - `hasOverride` tells us whether the user already customized an item. **Don't
    overwrite customized items without explicit approval** (this fits our
    approval flow).
  - `Reset Item SEO Tags To Default` is a native rollback path.
  - Known quirk: Get/List read the **draft** revision while Set with
    `publish:true` writes live, so we need to track our own state (we do, in
    `fixes.previous_state`).
- **Embedded Script API**: an app injects a script into `<head>` with dynamic
  parameters (our site key). Needs the app installed.
- **No API to edit body copy** of placed components on Editor/Studio pages.
  Content fixes are manual, or blog drafts.
- Manual path: Settings → Custom Code (head) for the snippet; per-page SEO panel for meta.

## Rendering
Wix serves server-rendered HTML to bots, but the raw-vs-rendered diff should
decide per page. Check Settings → SEO → Crawlers settings in audits (verify the
exact current UI label).

## Delivery mapping
| Fix | Delivery |
|---|---|
| Meta | Item SEO Tags (server-side) |
| Schema | Item SEO Tags structured-data tag (verify exact tag type in Phase 4); fallback: snippet |
| Content/FAQ | Manual instructions (UI steps) or blog draft |

## Platform rules (audit)
- Default titles "Home | My Site", un-customized SEO patterns.
- Hash-bang / dynamic pages not indexable, missing alt text on gallery images.
- Duplicate multilingual pages without proper hreflang (Wix Multilingual).
