import { useSites } from "@/lib/queries";
import { useSession } from "@/stores/session";
import { resolveSelectedSite, useSelectedSiteStore } from "@/stores/site";

/** Selected website for the current org, shared by every page. */
export function useSelectedSite(): [string | undefined, (siteId: string) => void] {
  const sites = useSites();
  const orgId = useSession((s) => s.currentOrgId);
  const stored = useSelectedSiteStore((s) => (orgId ? s.byOrg[orgId] : undefined));
  const select = useSelectedSiteStore((s) => s.select);
  return [resolveSelectedSite(sites.data, stored), (id) => orgId && select(orgId, id)];
}
