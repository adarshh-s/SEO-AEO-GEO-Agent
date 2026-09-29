import type { LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { EmptyState, PageHeader } from "@/components/ui/states";

/** Sections built in later phases. Kept in the nav so the product shape is visible. */
export function PlaceholderPage({ section, icon }: { section: string; icon: LucideIcon }) {
  const { t } = useTranslation("app");
  return (
    <>
      <PageHeader
        title={t(`sections.${section}.title`)}
        description={t(`sections.${section}.description`)}
      />
      <EmptyState
        icon={icon}
        title={t("sections.emptyTitle")}
        description={t(`sections.${section}.empty`)}
      />
    </>
  );
}
