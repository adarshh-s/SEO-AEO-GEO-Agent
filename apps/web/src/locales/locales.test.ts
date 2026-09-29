const files = import.meta.glob<{ default: Record<string, unknown> }>("./*/*.json", { eager: true });

function flatten(obj: unknown, prefix = ""): string[] {
  if (obj === null || typeof obj !== "object" || Array.isArray(obj)) return [prefix];
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
    flatten(v, prefix ? `${prefix}.${k}` : k),
  );
}

const PLURAL = /_(zero|one|two|few|many|other)$/;
const byLang: Record<string, Record<string, Set<string>>> = {};
for (const [path, mod] of Object.entries(files)) {
  const [, lang, ns] = path.match(/\.\/([^/]+)\/([^/]+)\.json$/)!;
  (byLang[lang!] ??= {})[ns!] = new Set(flatten(mod.default).map((k) => k.replace(PLURAL, "")));
}

describe("locale files", () => {
  it("English is the complete source: every translated key exists in English", () => {
    for (const [lang, namespaces] of Object.entries(byLang)) {
      if (lang === "en") continue;
      for (const [ns, keys] of Object.entries(namespaces)) {
        const en = byLang.en?.[ns];
        expect(en, `${lang}/${ns}.json has no English source`).toBeDefined();
        const orphans = [...keys].filter((k) => !en!.has(k));
        expect(orphans, `${lang}/${ns}.json keys missing in English`).toEqual([]);
      }
    }
  });
});
