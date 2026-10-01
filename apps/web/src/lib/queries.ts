import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type {
  AdminOrgOut,
  InvitationOut,
  KeywordOut,
  MemberOut,
  OrgOut,
  PlanOut,
  PromptOut,
  SiteOut,
  SiteUpdateIn,
  UserOut,
} from "./api-types";
import { useSession } from "@/stores/session";

/** Query keys include the org so switching orgs never shows another org's cache. */
export function useOrgKey() {
  return useSession((s) => s.currentOrgId);
}

export function useOrg() {
  const org = useOrgKey();
  return useQuery({ queryKey: ["org", org], queryFn: () => api<OrgOut>("/org"), enabled: !!org });
}

export function useSites() {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["sites", org],
    queryFn: () => api<SiteOut[]>("/sites"),
    enabled: !!org,
  });
}

export function useSite(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["site", org, siteId],
    queryFn: () => api<SiteOut>(`/sites/${siteId}`),
    enabled: !!org && !!siteId,
  });
}

export function useUpdateSite(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SiteUpdateIn) => api<SiteOut>(`/sites/${siteId}`, { method: "PATCH", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["site"] });
      void qc.invalidateQueries({ queryKey: ["sites"] });
    },
  });
}

export function useKeywords(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["keywords", org, siteId],
    queryFn: () => api<KeywordOut[]>(`/sites/${siteId}/keywords`),
    enabled: !!org && !!siteId,
  });
}

export function usePrompts(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["prompts", org, siteId],
    queryFn: () => api<PromptOut[]>(`/sites/${siteId}/prompts`),
    enabled: !!org && !!siteId,
  });
}

export function useMembers() {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["members", org],
    queryFn: () => api<MemberOut[]>("/org/members"),
    enabled: !!org,
  });
}

export function useInvitations(enabled: boolean) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["invitations", org],
    queryFn: () => api<InvitationOut[]>("/org/invitations"),
    enabled: !!org && enabled,
  });
}

export function usePublicPlans() {
  return useQuery({
    queryKey: ["plans"],
    queryFn: () => api<PlanOut[]>("/plans"),
    staleTime: 3600_000,
  });
}

export function useAdminOrgs(enabled: boolean) {
  return useQuery({
    queryKey: ["admin-orgs"],
    queryFn: () => api<AdminOrgOut[]>("/admin/orgs"),
    enabled,
  });
}

export function useAdminPlans(enabled: boolean) {
  return useQuery({
    queryKey: ["admin-plans"],
    queryFn: () => api<PlanOut[]>("/admin/plans"),
    enabled,
  });
}

export async function saveUiLanguage(lang: string): Promise<UserOut> {
  const user = await api<UserOut>("/auth/me", { method: "PATCH", body: { ui_language: lang } });
  useSession.getState().setUser(user);
  return user;
}

export function useRankings(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["rankings", org, siteId],
    queryFn: () => api<import("./api-types").RankedKeywordOut[]>(`/sites/${siteId}/rankings`),
    enabled: !!org && !!siteId,
  });
}

export function useAiVisibility(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["ai-visibility", org, siteId],
    queryFn: () =>
      api<
        | import("./api-types").AiVisibilitySummaryOut[]
        | import("./api-types").AiVisibilitySummaryOut
      >(`/sites/${siteId}/ai-visibility`),
    enabled: !!org && !!siteId,
  });
}

export function usePromptRuns(siteId: string | undefined, promptId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["prompt-runs", org, siteId, promptId],
    queryFn: () =>
      api<import("./api-types").AiCheckRunOut[]>(`/sites/${siteId}/prompts/${promptId}/runs`),
    enabled: !!org && !!siteId && !!promptId,
  });
}

export function useLatestCrawl(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["crawl-latest", org, siteId],
    queryFn: () => api<import("./api-types").CrawlSnapshotOut>(`/sites/${siteId}/crawl/latest`),
    enabled: !!org && !!siteId,
  });
}

export function useSiteOverview(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["overview", org, siteId],
    queryFn: () => api<import("./api-types").SiteOverviewOut>(`/sites/${siteId}/overview`),
    enabled: !!org && !!siteId,
  });
}

export function useTriggerKeywordCheck(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keywordId: string) =>
      api(`/sites/${siteId}/keywords/${keywordId}/check`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["rankings"] });
      void qc.invalidateQueries({ queryKey: ["overview"] });
    },
  });
}

export function useTriggerAllKeywordChecks(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api(`/sites/${siteId}/keywords/check-all`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["rankings"] });
      void qc.invalidateQueries({ queryKey: ["overview"] });
    },
  });
}

export function useTriggerPromptCheck(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (promptId: string) =>
      api(`/sites/${siteId}/prompts/${promptId}/check`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["ai-visibility"] });
      void qc.invalidateQueries({ queryKey: ["overview"] });
    },
  });
}

export function useTriggerAllPromptChecks(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api(`/sites/${siteId}/prompts/check-all`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["ai-visibility"] });
      void qc.invalidateQueries({ queryKey: ["overview"] });
    },
  });
}

export function useTriggerCrawl(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api(`/sites/${siteId}/crawl`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["crawl-latest"] });
      void qc.invalidateQueries({ queryKey: ["site"] });
    },
  });
}
