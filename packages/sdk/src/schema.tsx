import React from "react";
import type { QuardLinkFix } from "./metadata.js";

declare const process: { env?: Record<string, string | undefined> } | undefined;

export interface QuardLinkSchemaProps {
  siteKey: string;
  url: string;
  apiUrl?: string;
  revalidate?: number;
  fallbackSchema?: Record<string, unknown>;
}

const DEFAULT_API_URL = "https://api.quardlink.com";

/**
 * Server component that fetches approved JSON-LD schema for a URL and renders it server-side.
 * Fully compatible with Next.js App Router and React Server Components.
 */
export async function QuardLinkSchema({
  siteKey,
  url,
  apiUrl = (typeof process !== "undefined" &&
    process?.env?.NEXT_PUBLIC_QUARDLINK_API_URL) ||
    DEFAULT_API_URL,
  revalidate = 300,
  fallbackSchema,
}: QuardLinkSchemaProps): Promise<React.JSX.Element | null> {
  try {
    const cleanApi = apiUrl.replace(/\/+$/, "");
    const endpoint = `${cleanApi}/public/v1/fixes?site_key=${encodeURIComponent(siteKey)}&url=${encodeURIComponent(url)}`;

    const fetchOptions: RequestInit & { next?: { revalidate: number } } = {
      headers: { "User-Agent": "QuardLink-SDK/1.0" },
      next: { revalidate },
    };

    const res = await fetch(endpoint, fetchOptions);

    if (!res.ok) {
      if (fallbackSchema) {
        return (
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(fallbackSchema) }}
          />
        );
      }
      return null;
    }

    const data = (await res.json()) as { fixes?: QuardLinkFix[] };
    const fixes = data.fixes || [];
    const schemaFix = fixes.find((f) => f.type === "schema");

    const schemaToRender = schemaFix?.payload || fallbackSchema;
    if (!schemaToRender) {
      return null;
    }

    return (
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaToRender) }}
      />
    );
  } catch (_e) {
    if (fallbackSchema) {
      return (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(fallbackSchema) }}
        />
      );
    }
    return null;
  }
}
