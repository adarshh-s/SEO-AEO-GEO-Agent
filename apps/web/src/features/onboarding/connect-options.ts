import type { Platform } from "@/lib/api-types";

/** How each platform connects (CLAUDE.md §6, docs/platforms). Labels/steps live in i18n. */
export type ConnectKind = "automatic" | "paste" | "manual";
export type ConnectOption = { method: string; kind: ConnectKind; serverSide: boolean };

const SNIPPET: ConnectOption = { method: "snippet", kind: "paste", serverSide: false };
const MANUAL: ConnectOption = { method: "manual", kind: "manual", serverSide: true };

export const CONNECT_OPTIONS: Record<Platform, ConnectOption[]> = {
  wordpress: [{ method: "wpPlugin", kind: "automatic", serverSide: true }, SNIPPET, MANUAL],
  shopify: [{ method: "shopifyApp", kind: "automatic", serverSide: true }, SNIPPET, MANUAL],
  wix: [{ method: "wixApp", kind: "automatic", serverSide: true }, SNIPPET, MANUAL],
  webflow: [{ method: "webflowApp", kind: "automatic", serverSide: true }, MANUAL, SNIPPET],
  squarespace: [SNIPPET, MANUAL],
  framer: [SNIPPET, MANUAL],
  salla: [SNIPPET, MANUAL],
  zid: [SNIPPET, MANUAL],
  nextjs: [
    { method: "sdk", kind: "automatic", serverSide: true },
    { method: "api", kind: "automatic", serverSide: true },
    SNIPPET,
  ],
  nuxt: [
    { method: "sdk", kind: "automatic", serverSide: true },
    { method: "api", kind: "automatic", serverSide: true },
    SNIPPET,
  ],
  astro: [
    { method: "sdk", kind: "automatic", serverSide: true },
    { method: "api", kind: "automatic", serverSide: true },
    SNIPPET,
  ],
  react_spa: [
    SNIPPET,
    { method: "sdk", kind: "automatic", serverSide: true },
    { method: "api", kind: "automatic", serverSide: true },
  ],
  vue_spa: [
    SNIPPET,
    { method: "sdk", kind: "automatic", serverSide: true },
    { method: "api", kind: "automatic", serverSide: true },
  ],
  static: [
    { method: "github", kind: "automatic", serverSide: true },
    { method: "edgeWorker", kind: "automatic", serverSide: true },
    SNIPPET,
    MANUAL,
  ],
  custom_backend: [
    { method: "github", kind: "automatic", serverSide: true },
    { method: "api", kind: "automatic", serverSide: true },
    SNIPPET,
    MANUAL,
  ],
  unknown: [SNIPPET, MANUAL],
};

export const PLATFORMS = Object.keys(CONNECT_OPTIONS) as Platform[];
