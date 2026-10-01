# @quardlink/sdk

Official developer package for server-side SEO and AI search visibility (AEO) in Next.js, React, and modern web frameworks.

## Installation

```bash
npm install @quardlink/sdk
# or
pnpm add @quardlink/sdk
# or
yarn add @quardlink/sdk
```

## Quick Start (Next.js App Router)

### 1. Dynamic Page Metadata (`generateMetadata`)

In your Next.js App Router `page.tsx` or `layout.tsx`:

```tsx
import type { Metadata } from "next";
import { getQuardLinkMetadata } from "@quardlink/sdk";

export async function generateMetadata(): Promise<Metadata> {
  const defaultMeta: Metadata = {
    title: "Default Store Title",
    description: "Our awesome products",
  };

  return await getQuardLinkMetadata({
    siteKey: process.env.NEXT_PUBLIC_QUARDLINK_SITE_KEY!,
    url: "https://example.com/products/headphones",
    defaultMetadata: defaultMeta,
    revalidate: 300, // Stale-while-revalidate (5 minutes)
  });
}

export default function Page() {
  return <h1>Product Details</h1>;
}
```

### 2. Server-side Structured Data (`QuardLinkSchema`)

Render JSON-LD schema server-side so Google and AI search crawlers (GPTBot, PerplexityBot, ClaudeBot) read it without requiring JavaScript execution:

```tsx
import { QuardLinkSchema } from "@quardlink/sdk";

export default function Page() {
  return (
    <main>
      <h1>Product Details</h1>
      {/* Renders <script type="application/ld+json"> server-side */}
      <QuardLinkSchema
        siteKey={process.env.NEXT_PUBLIC_QUARDLINK_SITE_KEY!}
        url="https://example.com/products/headphones"
      />
    </main>
  );
}
```

## Resilience & Fail-Open Guarantee

`@quardlink/sdk` is strictly fail-open: if network issues or outages occur between your server and the QuardLink API, your application continues rendering with default metadata and existing templates without crashing or slowing down page requests.
