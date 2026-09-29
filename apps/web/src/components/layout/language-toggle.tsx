import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { applyLanguage, SUPPORTED_LANGUAGES } from "@/lib/i18n";
import { saveUiLanguage } from "@/lib/queries";
import { useSession } from "@/stores/session";

/** Header toggle. English is the default; the choice is saved per user when signed in. */
export function LanguageToggle() {
  const { t, i18n } = useTranslation();
  const signedIn = useSession((s) => !!s.user);
  const current = i18n.language;
  const next = SUPPORTED_LANGUAGES.find((l) => l !== current) ?? "en";

  async function change(lang: string) {
    await applyLanguage(lang);
    if (signedIn) {
      try {
        await saveUiLanguage(lang);
      } catch {
        /* UI already switched; saving is retried next time */
      }
    }
  }

  if (SUPPORTED_LANGUAGES.length > 2) {
    return (
      <label className="inline-flex items-center gap-2 text-sm">
        <Languages className="size-4" aria-hidden />
        <span className="sr-only">{t("language.label")}</span>
        <select
          value={current}
          onChange={(e) => void change(e.target.value)}
          className="bg-transparent"
        >
          {SUPPORTED_LANGUAGES.map((l) => (
            <option key={l} value={l}>
              {t("language.name", { lng: l })}
            </option>
          ))}
        </select>
      </label>
    );
  }
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => void change(next)}
      aria-label={t("language.switchTo", { language: t("language.name", { lng: next }) })}
      lang={next}
    >
      <Languages className="size-4" aria-hidden />
      {t("language.name", { lng: next })}
    </Button>
  );
}
