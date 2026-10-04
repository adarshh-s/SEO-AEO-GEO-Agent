# SDK for Next.js / React

Generated package name and branding come from `config/brand.json` (see `scripts/brand_sync.py`).

Loads the fixes you approved in the dashboard **on the server**, so search engines and AI
crawlers that don't run JavaScript still see them.

```bash
npm install <sdk_package from config/brand.json>
```

## Next.js App Router

```tsx
import { getSeoMetadata, StructuredData } from "<sdk_package>";

export async function generateMetadata() {
  return getSeoMetadata({
    siteKey: process.env.SITE_KEY!,
    url: "https://example.com/pricing",
    defaultMetadata: { title: "Pricing" },
  });
}

export default function Page() {
  return (
    <>
      <StructuredData siteKey={process.env.SITE_KEY!} url="https://example.com/pricing" />
      <main>…</main>
    </>
  );
}
```

- API URL: `apiUrl` option, else env `<BRAND_SLUG>_API_URL` (e.g. `OMNIRANK_API_URL`), else the public API.
- Fail-open: if the API is unreachable your page renders with its own metadata.
- JSON-LD is escaped so it can never close the `<script>` element.
