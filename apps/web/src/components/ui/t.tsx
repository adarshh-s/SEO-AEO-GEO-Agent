import { useTranslation } from "react-i18next";

/** Inline translated text: <T k="file.key" />, keys live in locales/<lang>/ui.json. */
export function T({ k }: { k: string }) {
  const { t } = useTranslation("ui");
  return <>{t(k)}</>;
}
