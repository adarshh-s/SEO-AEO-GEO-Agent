# Google Search Console

Sources: [Authorize requests](https://developers.google.com/webmaster-tools/v1/how-tos/authorizing) (checked 2026-09-29).

- Scopes: `https://www.googleapis.com/auth/webmasters.readonly` (read-only) or
  `.../webmasters` (read/write). **We request read-only only.**
- Uses: `sites.list` (match the customer's property: URL-prefix or
  `sc-domain:`), `searchanalytics.query` (clicks, impressions, CTR, position by
  query/page/country/device, 16 months), URL Inspection (index status).
- Upstream `gsc_query.py` / `gsc_inspect.py` hold pagination and aggregation
  logic we'll port.
- **Google OAuth app verification**: Search Console scopes are classed as
  sensitive, so a production OAuth consent screen needs Google verification
  (privacy policy, homepage, demo video; takes days to weeks). Start this early
  (Phase 4 at the latest). Verify the current classification in the Google Cloud
  console. Until verified, we're capped at 100 test users.
- GSC property verification can double as **ownership verification** for our
  site (a user who is a verified owner in GSC counts as verified).
