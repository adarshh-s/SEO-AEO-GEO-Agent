/// <reference types="node" />
/**
 * The universal snippet (apps/api/app_api/static/agent.js) against sample pages:
 * static, SPA shell, Wix-like and Shopify-like (CLAUDE.md §11). Runs the real file with the
 * brand placeholders filled in, exactly as /public/v1/agent.js serves it.
 */
import fs from "node:fs";
import path from "node:path";
import { gzipSync } from "node:zlib";
import { BRAND } from "@/lib/brand.gen";

// Vitest runs from apps/web.
const RAW = fs.readFileSync(path.resolve(process.cwd(), "../api/app_api/static/agent.js"), "utf8");
const SRC = RAW.replaceAll("__BRAND_GLOBAL__", BRAND.snippet_global).replaceAll(
  "__BRAND_SLUG__",
  BRAND.brand_slug,
);
const SLUG = BRAND.brand_slug;

const PAGES = {
  static: `<head><title>Bright Smile</title></head><body><h1>Dentist</h1><p>Hello</p></body>`,
  spa: `<head><title>App</title></head><body><div id="root"></div></body>`,
  wix: `<head><title>Home | My Site</title><meta name="description" content="Old description">
        <script>window.wixBiSession={}</script></head><body><div id="SITE_CONTAINER"></div></body>`,
  shopify: `<head><title>Oud</title><script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","name":"Oud Oil"}</script></head>
        <body><main><div data-${SLUG}-content></div></main></body>`,
};

type Fix = { id: string; type: string; target_url: string; payload: Record<string, unknown> };

function load(
  page: keyof typeof PAGES,
  opts: { fixes?: Fix[]; referrer?: string; fetchImpl?: () => Promise<Response> } = {},
) {
  document.documentElement.innerHTML = PAGES[page];
  const tag = document.createElement("script");
  tag.setAttribute("data-site", "qls_test");
  tag.setAttribute("src", "https://api.example.com/public/v1/agent.js");
  document.head.appendChild(tag);
  delete (window as unknown as Record<string, unknown>)[BRAND.snippet_global];
  Object.defineProperty(document, "referrer", { value: opts.referrer ?? "", configurable: true });
  const fetchMock = vi.fn(
    opts.fetchImpl ??
      (async () => new Response(JSON.stringify({ fixes: opts.fixes ?? [] }), { status: 200 })),
  );
  vi.stubGlobal("fetch", fetchMock);
  const beacon = vi.fn(() => true);
  Object.defineProperty(navigator, "sendBeacon", { value: beacon, configurable: true });
  new Function(SRC)();
  return { fetchMock, beacon };
}

const flush = async () => {
  for (let i = 0; i < 5; i++) await new Promise((r) => setTimeout(r, 0));
};

const schemaFix: Fix = {
  id: "f1",
  type: "schema",
  target_url: "https://x/",
  payload: {
    json_ld: { "@context": "https://schema.org", "@type": "Dentist", name: "Bright Smile" },
  },
};
const metaFix: Fix = {
  id: "f2",
  type: "meta",
  target_url: "https://x/",
  payload: {
    title: "Dentist in Austin | Bright Smile",
    meta_description: "Gentle family dentist.",
  },
};
const contentFix: Fix = {
  id: "f3",
  type: "content_block",
  target_url: "https://x/",
  payload: { html: "<h2>Prices</h2><p>From $50</p>" },
};

afterEach(() => vi.unstubAllGlobals());

describe("universal snippet", () => {
  it("is small: under 15 KB gzipped", () => {
    expect(gzipSync(SRC).length).toBeLessThan(15_000);
  });

  it("asks the API for this page's fixes with the site key", async () => {
    const { fetchMock } = load("static");
    await flush();
    const url = String((fetchMock.mock.calls[0] as unknown[])[0]);
    expect(url.startsWith("https://api.example.com/public/v1/fixes?site_key=qls_test&url=")).toBe(
      true,
    );
  });

  it("static page: adds JSON-LD, updates title and creates the meta description", async () => {
    load("static", { fixes: [schemaFix, metaFix] });
    await flush();
    const ld = document.head.querySelector('script[type="application/ld+json"]');
    expect(JSON.parse(ld!.textContent!)["@type"]).toBe("Dentist");
    expect(document.title).toBe("Dentist in Austin | Bright Smile");
    expect(document.querySelector('meta[name="description"]')?.getAttribute("content")).toBe(
      "Gentle family dentist.",
    );
  });

  it("Wix-like page: replaces the existing meta description instead of duplicating it", async () => {
    load("wix", { fixes: [metaFix] });
    await flush();
    const metas = document.querySelectorAll('meta[name="description"]');
    expect(metas).toHaveLength(1);
    expect(metas[0]!.getAttribute("content")).toBe("Gentle family dentist.");
  });

  it("Shopify-like page: keeps the theme's schema and adds ours", async () => {
    load("shopify", { fixes: [schemaFix] });
    await flush();
    const types = [...document.querySelectorAll('script[type="application/ld+json"]')].map(
      (s) => JSON.parse(s.textContent!)["@type"],
    );
    expect(types).toEqual(["Product", "Dentist"]);
  });

  it("content blocks only go into a container the customer placed (D15)", async () => {
    load("spa", { fixes: [contentFix] });
    await flush();
    expect(document.body.innerHTML).not.toContain("Prices"); // no container: nothing injected

    load("shopify", { fixes: [contentFix] });
    await flush();
    const container = document.querySelector(`[data-${SLUG}-content]`)!;
    expect(container.innerHTML).toContain("<h2>Prices</h2>");
  });

  it.each([
    ["network error", () => Promise.reject(new TypeError("offline"))],
    ["server error", async () => new Response("oops", { status: 500 })],
    ["malformed JSON", async () => new Response("{not json", { status: 200 })],
    ["unexpected shape", async () => new Response(JSON.stringify({ fixes: [{ type: "meta" }] }))],
  ])("never breaks the host page on %s", async (_name, fetchImpl) => {
    const errors: unknown[] = [];
    const onError = (e: ErrorEvent) => errors.push(e.error);
    window.addEventListener("error", onError);
    expect(() => load("static", { fetchImpl })).not.toThrow();
    await flush();
    window.removeEventListener("error", onError);
    expect(errors).toEqual([]);
    expect(document.querySelector("h1")?.textContent).toBe("Dentist");
  });

  it("runs only once if the snippet is pasted twice", async () => {
    const { fetchMock } = load("static");
    new Function(SRC)();
    await flush();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("pings AI referrals cookielessly, and only for AI referrers", async () => {
    const ai = load("static", { referrer: "https://chatgpt.com/" });
    await flush();
    expect(ai.beacon).toHaveBeenCalledTimes(1);
    const [url, body] = ai.beacon.mock.calls[0] as unknown as [string, string];
    expect(url).toBe("https://api.example.com/public/v1/telemetry/referral");
    expect(JSON.parse(body)).toMatchObject({ site_key: "qls_test", referrer_engine: "chatgpt" });
    expect(document.cookie).toBe("");

    const other = load("static", { referrer: "https://www.google.com/" });
    await flush();
    expect(other.beacon).not.toHaveBeenCalled();
  });
});
