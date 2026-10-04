import { create } from "zustand";
import type { SiteOut } from "@/lib/api-types";

const KEY = "app.selectedSite";

function read(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "{}") as Record<string, string>;
  } catch {
    return {};
  }
}

/** The website chosen in any page's picker, remembered per organization across pages. */
export const useSelectedSiteStore = create<{
  byOrg: Record<string, string>;
  select: (orgId: string, siteId: string) => void;
}>((set, get) => ({
  byOrg: read(),
  select: (orgId, siteId) => {
    const byOrg = { ...get().byOrg, [orgId]: siteId };
    try {
      localStorage.setItem(KEY, JSON.stringify(byOrg));
    } catch {
      /* storage unavailable */
    }
    set({ byOrg });
  },
}));

/** [selected site id (falls back to the first site), setter]. Ignores stale/foreign ids. */
export function resolveSelectedSite(
  sites: SiteOut[] | undefined,
  stored: string | undefined,
): string | undefined {
  return sites?.find((s) => s.id === stored)?.id ?? sites?.[0]?.id;
}
