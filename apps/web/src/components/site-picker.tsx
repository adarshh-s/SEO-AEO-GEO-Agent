import { useTranslation } from "react-i18next";
import { useSites } from "@/lib/queries";
import { useSelectedSite } from "@/lib/use-selected-site";

export function SitePicker() {
  const { t } = useTranslation("app");
  const sites = useSites();
  const [siteId, setSiteId] = useSelectedSite();
  if (!sites.data || sites.data.length < 2) return null;
  return (
    <label className="flex items-center gap-2">
      <span className="text-muted-foreground text-sm font-medium">{t("overview.sites")}:</span>
      <select
        value={siteId}
        onChange={(e) => setSiteId(e.target.value)}
        className="border-input bg-background focus-visible:ring-ring rounded-md border px-3 py-1.5 text-sm focus-visible:ring-2 focus-visible:outline-none"
      >
        {sites.data.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name || s.domain}
          </option>
        ))}
      </select>
    </label>
  );
}
