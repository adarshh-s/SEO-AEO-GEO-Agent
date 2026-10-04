import React from "react";
import { fetchFixes, type FetchOptions } from "./metadata.js";

export interface StructuredDataProps extends FetchOptions {
  /** Rendered when no approved schema exists for the page (or on error). */
  fallbackSchema?: Record<string, unknown>;
}

/** JSON for an HTML <script> element: escape <, > and & so it can never close the tag. */
export function jsonLdScriptText(value: unknown): string {
  return JSON.stringify(value)
    .replace(/</g, "\\u003c")
    .replace(/>/g, "\\u003e")
    .replace(/&/g, "\\u0026");
}

function JsonLd({ value }: { value: unknown }) {
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLdScriptText(value) }} />;
}

/**
 * Server component rendering approved JSON-LD for a page server-side, so AI crawlers
 * that don't run JavaScript still see it. Works with the Next.js App Router / RSC.
 */
export async function StructuredData({ fallbackSchema, ...options }: StructuredDataProps) {
  const fixes = await fetchFixes(options);
  const schemas = fixes.flatMap((f) => (f.payload.json_ld ? [f.payload.json_ld] : []));
  if (schemas.length === 0) return fallbackSchema ? <JsonLd value={fallbackSchema} /> : null;
  return (
    <>
      {schemas.map((schema, i) => (
        <JsonLd key={i} value={schema} />
      ))}
    </>
  );
}
