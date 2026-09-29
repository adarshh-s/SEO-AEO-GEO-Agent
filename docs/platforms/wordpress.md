# WordPress

Sources: [Detailed Plugin Guidelines](https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/) (checked 2026-09-29).

## Capabilities
- Full server-side control through a plugin: `wp_head` for JSON-LD and meta,
  `pre_get_document_title` / `document_title_parts` for titles, the REST API
  (`/wp-json/wp/v2/posts`) for draft posts (`status=draft`).
- Head code without our plugin: a theme `header.php` edit or a generic "insert
  headers" plugin (manual fallback).

## Plugin design (Phase 4)
- Connects to RankAgent with a site key + signed token (application-password
  style), pulls approved fixes from our API on a schedule (WP-Cron) and on a
  webhook ping, caches them in a transient/option, and renders them in PHP.
- **Detect and cooperate with Yoast / Rank Math / AIOSEO / SEOPress**: when one
  is active, write to *their* fields (Yoast `_yoast_wpseo_title` and
  `_yoast_wpseo_metadesc` post meta, Rank Math `rank_math_title` and
  `rank_math_description`) instead of outputting a second `<title>`/meta. For
  schema, merge into their graph via filters (`wpseo_schema_graph`,
  `rank_math/json_ld`) rather than printing a duplicate block. Verify these hook
  names against current plugin docs in Phase 4.
- Content fixes go out as **draft** posts/pages only (never publish).
- Rollback: the plugin stores the previous value per fix, and our API keeps
  `previous_state` too.
- AI referral + AI crawler logging: done **server-side in PHP** (inspect the
  `Referer` and `User-Agent` headers, batch-send counts). This is more reliable
  than JS and catches bots.

## wp.org guideline constraints
- **G6** SaaS/serviceware plugins are allowed, even for paid services.
- **G7** No contacting external servers without explicit consent. The plugin
  does nothing until the admin connects it, and the readme documents what is
  sent, with a privacy policy link.
- **G8** Don't load JS/CSS from third-party CDNs. The plugin must NOT enqueue
  our `agent.js` from our CDN. It renders fixes server-side, which is what we
  want anyway.
- **G4** No obfuscated code. **G5** No locked features (paid features must be
  the SaaS itself). **G11** Admin notices must be minimal and dismissible.

## Platform rules (audit)
- Multiple SEO plugins active → duplicate title/meta/schema.
- `Discourage search engines` (blog_public=0) turned on.
- Duplicate archive/tag/author pages without noindex, attachment pages indexed.
- Caching plugins serving stale head after fix (purge hooks: WP Rocket, LiteSpeed, W3TC).
