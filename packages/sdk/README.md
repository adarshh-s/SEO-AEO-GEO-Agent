# @omnirank/sdk

Official developer package for server-side SEO, Answer Engine Optimization (AEO), and Generative Engine Optimization (GEO) in Next.js, React, and modern web frameworks.

## Installation

```bash
npm install @omnirank/sdk
# or
pnpm add @omnirank/sdk
# or
yarn add @omnirank/sdk
```

## Quick Start (Next.js App Router)

### 1. Dynamic Page Metadata (`generateMetadata`)

In your Next.js App Router `page.tsx` or `layout.tsx`:

```tsx
import type { Metadata } from "next";
import { getOmniRankMetadata } from "@omnirank/sdk";

export async function generateMetadata(): Promise<Metadata> {
  const defaultMeta: Metadata = {
    title: "Default Store Title",
    description: "Our awesome products",
  };

  return await getOmniRankMetadata({
    siteKey: process.env.NEXT_PUBLIC_OMNIRANK_SITE_KEY!,
    url: "https://example.com/products/headphones",
    defaultMetadata: defaultMeta,
    revalidate: 300, // Stale-while-revalidate (5 minutes)
  });
}

export default function Page() {
  return <h1>Product Details</h1>;
}
```

### 2. Server-side Structured Data (`OmniRankSchema`)

Render JSON-LD schema server-side so Google and AI search crawlers (GPTBot, PerplexityBot, ClaudeBot, Google-Extended) read it without requiring client JavaScript execution:

```tsx
import { OmniRankSchema } from "@omnirank/sdk";

export default function Page() {
  return (
    <main>
      <h1>Product Details</h1>
      {/* Renders <script type="application/ld+json"> server-side */}
      <OmniRankSchema
        siteKey={process.env.NEXT_PUBLIC_OMNIRANK_SITE_KEY!}
        url="https://example.com/products/headphones"
      />
    </main>
  );
}
```

## Resilience & Fail-Open Guarantee

`@omnirank/sdk` is strictly fail-open: if network issues or outages occur between your server and the OmniRank API, your application continues rendering with default metadata and existing templates without crashing or slowing down page requests.
