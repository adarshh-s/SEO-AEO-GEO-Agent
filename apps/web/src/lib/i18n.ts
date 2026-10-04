import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import { PRODUCT_NAME } from "./brand";

/**
 * Locales are discovered from src/locales/<code>/<namespace>.json.
 * Add a language by adding a folder (English is the source; missing keys fall back to it).
 */
const files = import.meta.glob<{ default: Record<string, unknown> }>("../locales/*/*.json", {
  eager: true,
});

const resources: Record<string, Record<string, Record<string, unknown>>> = {};
for (const [path, mod] of Object.entries(files)) {
  const match = path.match(/locales\/([^/]+)\/([^/]+)\.json$/);
  if (!match) continue;
  const [, lang, ns] = match as unknown as [string, string, string];
  (resources[lang] ??= {})[ns] = mod.default;
}

export const DEFAULT_LANGUAGE = "en";
// Interface languages offered to users (decision D22: English only for now). Comma-separated
// VITE_UI_LANGUAGES re-enables others, e.g. "en,ar" — no code changes needed.
const ENABLED = (import.meta.env.VITE_UI_LANGUAGES ?? DEFAULT_LANGUAGE)
  .split(",")
  .map((l: string) => l.trim())
  .filter(Boolean);
export const SUPPORTED_LANGUAGES = Object.keys(resources)
  .filter((l) => l === DEFAULT_LANGUAGE || ENABLED.includes(l))
  .sort((a, b) => (a === DEFAULT_LANGUAGE ? -1 : b === DEFAULT_LANGUAGE ? 1 : a.localeCompare(b)));
const RTL = new Set(["ar", "he", "fa", "ur"]);
const STORAGE_KEY = "app.uiLanguage";

export function isRtl(lang: string): boolean {
  return RTL.has(lang.split("-")[0] ?? lang);
}

export function normalizeLanguage(lang: string | null | undefined): string {
  return lang && SUPPORTED_LANGUAGES.includes(lang) ? lang : DEFAULT_LANGUAGE;
}

export function storedLanguage(): string {
  try {
    return normalizeLanguage(localStorage.getItem(STORAGE_KEY));
  } catch {
    return DEFAULT_LANGUAGE;
  }
}

/** Switch UI language: i18next + <html lang/dir> (RTL only for RTL languages) + remember. */
export async function applyLanguage(lang: string): Promise<void> {
  const code = normalizeLanguage(lang);
  await i18n.changeLanguage(code);
  document.documentElement.lang = code;
  document.documentElement.dir = isRtl(code) ? "rtl" : "ltr";
  try {
    localStorage.setItem(STORAGE_KEY, code);
  } catch {
    /* storage unavailable */
  }
}

/** Western digits by default in every language, including Arabic (decision D9). */
export function formatNumber(value: number, lang = i18n.language): string {
  return new Intl.NumberFormat(`${lang}-u-nu-latn`).format(value);
}

export function formatDate(value: string | Date, lang = i18n.language): string {
  return new Intl.DateTimeFormat(`${lang}-u-nu-latn`, { dateStyle: "medium" }).format(
    typeof value === "string" ? new Date(value) : value,
  );
}

void i18n.use(initReactI18next).init({
  resources,
  lng: DEFAULT_LANGUAGE,
  fallbackLng: DEFAULT_LANGUAGE,
  defaultNS: "common",
  ns: Object.keys(resources[DEFAULT_LANGUAGE] ?? {}),
  interpolation: { escapeValue: false, defaultVariables: { product: PRODUCT_NAME } },
  returnNull: false,
});

export default i18n;
