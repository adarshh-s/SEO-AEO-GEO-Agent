declare const process: { env?: Record<string, string | undefined> } | undefined;

export interface QuardLinkFix {
  id: string;
  type: "meta" | "schema" | "faq" | "content_block" | "technical";
  title: string;
  payload: {
    title?: string;
    meta_description?: string;
    html?: string;
    [key: string]: unknown;
  };
}

export interface GetMetadataOptions {
  siteKey: string;
  url: string;
  apiUrl?: string;
  revalidate?: number;
  defaultMetadata?: Record<string, unknown>;
}

const DEFAULT_API_URL = "https://api.quardlink.com";

/**
 * Fetch approved SEO metadata fixes and merge them into Next.js App Router metadata.
 * Fail-open: returns defaultMetadata unchanged on network or parsing error.
 */
export async function getQuardLinkMetadata(
  options: GetMetadataOptions,
): Promise<Record<string, unknown>> {
  const {
    siteKey,
    url,
    apiUrl = (typeof process !== "undefined" &&
      process?.env?.NEXT_PUBLIC_QUARDLINK_API_URL) ||
      DEFAULT_API_URL,
    revalidate = 300,
    defaultMetadata = {},
  } = options;

  try {
    const cleanApi = apiUrl.replace(/\/+$/, "");
    const endpoint = `${cleanApi}/public/v1/fixes?site_key=${encodeURIComponent(siteKey)}&url=${encodeURIComponent(url)}`;

    // Pass Next.js revalidation options if running in Next.js environment
    const fetchOptions: RequestInit & { next?: { revalidate: number } } = {
      headers: {
        "User-Agent": "QuardLink-SDK/1.0",
      },
      next: { revalidate },
    };

    const res = await fetch(endpoint, fetchOptions);
    if (!res.ok) {
      return defaultMetadata;
    }

    const data = (await res.json()) as { fixes?: QuardLinkFix[] };
    const fixes = data.fixes || [];

    const metaFix = fixes.find((f) => f.type === "meta");
    if (!metaFix || !metaFix.payload) {
      return defaultMetadata;
    }

    const merged: Record<string, unknown> = { ...defaultMetadata };
    if (metaFix.payload.title) {
      merged.title = metaFix.payload.title;
    }
    if (metaFix.payload.meta_description) {
      merged.description = metaFix.payload.meta_description;
    }

    return merged;
  } catch (_e) {
    // Fail-open: network errors never break page generation
    return defaultMetadata;
  }
}
