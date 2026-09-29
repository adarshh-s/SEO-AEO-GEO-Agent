# Registrations checklist

Nothing below has been registered yet. QuardLink is a test name and the legal
entity doesn't exist yet. Lead times are rough estimates from public docs;
re-check each program's current requirements when you start.

## 0. Prerequisites (almost everything below needs these)

| Item | Why |
|---|---|
| Registered legal entity (name, CR number, address) | Partner programs, Google OAuth verification and app stores list a publisher. Salla/Zid partner programs are KSA-oriented and may ask for a CR / Freelance document. |
| Domain `quardlink.com` + DNS access | App URLs, OAuth redirect URIs, and Google domain verification. |
| Public pages: homepage, **privacy policy**, **terms of service**, support/contact page, all on the domain | Required by Google OAuth verification, Shopify, Wix, Webflow, WordPress.org readme, Salla, Zid. |
| Support email on the domain (e.g. support@quardlink.com) | Listed on app listings and OAuth consent screen. |
| Logo (square, 512×512 and 1200×1200) and screenshots | All app listings. |
| Demo video (1–3 min, unlisted YouTube) | Google OAuth verification, Shopify review. |
| Test/demo accounts with seeded data | Reviewers must be able to log in. `SEED_DEMO=true` covers this. |

## 1. Google (Search Console OAuth + Google sign-in)

- **Where:** Google Cloud Console → a project → OAuth consent screen + credentials.
- **Needs:** verified domain ownership in Google Search Console (for the
  homepage/privacy URLs), privacy policy that explains the use of Google user
  data (Limited Use disclosure), scope justification for
  `webmasters.readonly`, demo video showing the OAuth flow and how the data is
  used, and authorized redirect URIs (`https://api.quardlink.com/...`).
- **Sign-in only** (`openid email profile`) is non-sensitive: brand
  verification only, quick.
- **Search Console scope** is classed as *sensitive* (verify the current
  classification in the console): it needs full verification. **Lead time: ~1–6
  weeks.** Until verified, the app is limited to 100 test users with an
  "unverified app" warning, which is fine for testing.
- API keys for PageSpeed Insights / CrUX: just a GCP project + API key, no review.

## 2. Shopify

- **Where:** Shopify Partner account (free) → create app → dev store for testing.
- **Needs for App Store listing:** listing content, privacy policy URL,
  mandatory GDPR webhooks (customers/data_request, customers/redact,
  shop/redact), embedded app using App Bridge, GraphQL Admin API only, theme
  app extension (no direct theme edits), performance and security checks,
  screencast, test credentials.
- **Lead time:** partner account same day. App review typically **1–4 weeks**,
  often with revision rounds. A custom/unlisted distribution to specific stores
  needs no App Store review (useful for early customers).

## 3. Wix

- **Where:** Wix Developers (dev.wix.com) account → create app → test site.
- **Needs for App Market:** listing, privacy policy, pricing info, permission
  justification (SEO + Embedded Scripts), test instructions.
- **Lead time:** account same day. Market review **~2–4 weeks**. Private/unlisted
  install on test sites works before review.

## 4. Webflow

- **Where:** Webflow workspace → Apps → register a Data Client app (OAuth).
- **Needs for Marketplace:** listing, privacy policy, scope justification
  (`pages:write`, `custom_code:write`, `cms:write`), demo video.
- **Lead time:** app registration same day. Marketplace review **~1–3 weeks**.
  Before approval the app can be installed on your own workspace sites for testing.

## 5. WordPress.org plugin directory

- **Where:** wordpress.org account → plugin submission.
- **Needs:** GPL-compatible plugin, readme.txt documenting the external
  service (what data is sent, links to terms + privacy policy), no
  obfuscation, no remote JS/CSS from our CDN, sanitized/escaped code.
- **Lead time:** review queue **~1–4 weeks**. Before approval, distribute as a
  zip from our site.

## 6. Salla (سلة)

- **Where:** Salla Partners portal (salla.partners) → create app → demo store.
- **Needs:** partner account (may require a KSA entity or freelance doc; check),
  app details in Arabic and English, OAuth callback URL, scopes (products
  read/write, store settings), App Snippet URL (our `agent.js` on the CDN),
  privacy policy, support contact, and testing on a demo store.
- **Review:** all apps (public or private) are reviewed before publishing.
  **Lead time: unknown, estimate 2–6 weeks.** Ask Salla partner support.

## 7. Zid (زد)

- **Where:** Zid Partner Dashboard (partner.zid.sa) → create app → dev store.
- **Needs:** partner account (likely KSA entity; check), app listing in AR/EN,
  OAuth details, App Script (snippet) submission, privacy policy, support contact.
- **Review:** app scripts and apps are reviewed. **Lead time: unknown, estimate
  2–6 weeks.** Ask Zid partner support.

## 8. GitHub App (PR integration)

- **Where:** GitHub → Settings → Developer settings → GitHub Apps (under an org
  account for QuardLink).
- **Needs:** name, homepage, callback + webhook URLs, minimal permissions
  (Contents: read/write, Pull requests: read/write, Metadata: read), webhook
  secret, private key.
- **Lead time:** same day. The Marketplace listing is optional.

## 9. Cloudflare (edge worker template)

- No registration needed to publish a template repo. Optional: a "Deploy to
  Cloudflare" button (needs a public GitHub repo).

## 10. API providers (keys only, no review)

| Provider | Needs | Notes |
|---|---|---|
| Anthropic | Console account + billing | Set spend limits in console. |
| OpenAI | Platform account + billing | Web search tool usage is billed separately. |
| Perplexity | API account + credits | |
| Google Gemini | AI Studio / GCP project key | Grounding with Google Search is billed per request. |
| DataForSEO | Account, $50 minimum deposit | $1 trial credit. |
| Resend | Account + verified sending domain (SPF/DKIM DNS records) | Domain verification needs the domain. |
| Sentry | Account (optional) | Free tier to start. |
| Railway / Vercel | Accounts + billing | Custom domains need DNS. |

## 11. Payments (Phase 7, listed so you can plan)

| Provider | Needs | Lead time |
|---|---|---|
| Moyasar | KSA CR, bank account (IBAN), website with policies (refund, terms, privacy), business owner ID | ~1–3 weeks onboarding |
| Tap Payments | Same kind of KYC documents; supports mada, Apple Pay, cards | ~1–3 weeks |
| Apple Pay (via Moyasar/Tap) | Domain verification file on the checkout domain | days |
| Stripe | Entity in a Stripe-supported country (KSA is not a direct Stripe country; a UAE or US entity may be needed; check) | days |

## Suggested order

1. Entity + domain → 2. public pages (privacy/terms) → 3. Google OAuth
verification (longest queue, start early) → 4. Shopify, Wix, Webflow, and WP
submissions in parallel once Phase 4 builds exist → 5. Salla/Zid when the
entity exists → 6. Payment KYC before Phase 7.
