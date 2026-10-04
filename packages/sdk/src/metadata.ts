import { BRAND } from "./brand.gen.js";

declare const process: { env?: Record<string, string | undefined> } | undefined;

export interface Fix {
  id: string;
  type: "meta" | "schema" | "faq" | "content_block" | "technical";
  target_url: string;
  payload: {
    title?: string;
    meta_description?: string;
    json_ld?: Record<string, unknown> | Record<string, unknown>[];
    html?: string;
  };
}

export interface FetchOptions {
  siteKey: string;
  url: string;
  /** Defaults to env `<BRAND_SLUG>_API_URL`, then the public API. */
  apiUrl?: string;
  /** Next.js ISR revalidation in seconds. */
  revalidate?: number;
}

export function resolveApiUrl(apiUrl?: string): string {
  const envName = `${BRAND.brand_slug.toUpperCase()}_API_URL`;
  const fromEnv = typeof process !== "undefined" ? process?.env?.[envName] : undefined;
  return (apiUrl || fromEnv || BRAND.public_api_url).replace(/\/+$/, "");
}

/** Approved fixes for a page. Fail-open: returns [] on any error. */
export async function fetchFixes({ siteKey, url, apiUrl, revalidate = 300 }: FetchOptions): Promise<Fix[]> {
  try {
    const endpoint =
      `${resolveApiUrl(apiUrl)}/public/v1/fixes` +
      `?site_key=${encodeURIComponent(siteKey)}&url=${encodeURIComponent(url)}`;
    const init: RequestInit & { next?: { revalidate: number } } = {
      headers: { "User-Agent": `${BRAND.product_name}-SDK/1.0` },
      next: { revalidate },
    };
    const res = await fetch(endpoint, init);
    if (!res.ok) return [];
    const data = (await res.json()) as { fixes?: Fix[] };
    return data.fixes ?? [];
  } catch {
    return [];
  }
}

export interface GetMetadataOptions extends FetchOptions {
  defaultMetadata?: Record<string, unknown>;
}

/**
 * Merge approved title/description fixes into Next.js App Router metadata
 * (use inside `generateMetadata`). Fail-open: returns defaultMetadata on error.
 */
export async function getSeoMetadata({
  defaultMetadata = {},
  ...options
}: GetMetadataOptions): Promise<Record<string, unknown>> {
  const metaFix = (await fetchFixes(options)).find((f) => f.type === "meta");
  const merged: Record<string, unknown> = { ...defaultMetadata };
  if (metaFix?.payload.title) merged.title = metaFix.payload.title;
  if (metaFix?.payload.meta_description) merged.description = metaFix.payload.meta_description;
  return merged;
}
