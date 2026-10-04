import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type {
  AdminAuditLogOut,
  AdminCostSummaryOut,
  AdminOrgCostDetailOut,
  AdminOrgOut,
  AdminPlanUpdateIn,
  ApiKeyCreatedOut,
  ApiKeyCreateIn,
  ApiKeyOut,
  AuditOut,
  AuditTriggerIn,
  DiagnosisOut,
  DiagnosisTriggerIn,
  DigestSendTestOut,
  FixDeployIn,
  FixOut,
  FixUpdateIn,
  InvitationOut,
  KeywordOut,
  MemberOut,
  OrgOut,
  PlanOut,
  PromptOut,
  ReportCreateIn,
  ReportOut,
  SiteIntegrationCreateIn,
  SiteIntegrationOut,
  SiteIntegrationUpdateIn,
  SiteOut,
  SiteUpdateIn,
  SnippetInfoOut,
  TestConnectionOut,
  GscAuthUrlOut,
  GscConnectIn,
  GscPerformanceOut,
  UserOut,
  VerificationStatusOut,
  VerifyAttemptOut,
  WebhookCreateIn,
  WebhookCreatedOut,
  WebhookOut,
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

export function useAdminCostSummary(enabled: boolean) {
  return useQuery({
    queryKey: ["admin-cost-summary"],
    queryFn: () => api<AdminCostSummaryOut>("/admin/costs/summary"),
    enabled,
  });
}

export function useAdminOrgCosts(orgId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["admin-org-costs", orgId],
    queryFn: () => api<AdminOrgCostDetailOut>(`/admin/orgs/${orgId}/costs`),
    enabled: enabled && !!orgId,
  });
}

export function useAdminResetCounters() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (orgId: string) =>
      api<{ ok: boolean; message: string }>(`/admin/orgs/${orgId}/reset-counters`, {
        method: "POST",
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-orgs"] });
      void qc.invalidateQueries({ queryKey: ["admin-cost-summary"] });
      void qc.invalidateQueries({ queryKey: ["admin-org-costs"] });
    },
  });
}

export function useAdminAuditLogs(enabled: boolean) {
  return useQuery({
    queryKey: ["admin-audit-logs"],
    queryFn: () => api<AdminAuditLogOut[]>("/admin/audit-logs"),
    enabled,
  });
}

export function useAdminUpdatePlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ code, body }: { code: string; body: AdminPlanUpdateIn }) =>
      api<PlanOut>(`/admin/plans/${code}`, { method: "PATCH", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-plans"] });
      void qc.invalidateQueries({ queryKey: ["plans"] });
    },
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

// --- Phase 3: Fixes ---

export function useFixes(
  siteId: string | undefined,
  filters?: { status?: string; type?: string; language?: string },
) {
  const org = useOrgKey();
  const params = new URLSearchParams();
  if (filters?.status && filters.status !== "all") params.set("status", filters.status);
  if (filters?.type && filters.type !== "all") params.set("type", filters.type);
  if (filters?.language && filters.language !== "all") params.set("language", filters.language);
  const qs = params.toString() ? `?${params.toString()}` : "";

  return useQuery({
    queryKey: ["fixes", org, siteId, filters],
    queryFn: () => api<FixOut[]>(`/sites/${siteId}/fixes${qs}`),
    enabled: !!org && !!siteId,
  });
}

export function useFix(siteId: string | undefined, fixId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["fix", org, siteId, fixId],
    queryFn: () => api<FixOut>(`/sites/${siteId}/fixes/${fixId}`),
    enabled: !!org && !!siteId && !!fixId,
  });
}

export function useUpdateFix(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ fixId, body }: { fixId: string; body: FixUpdateIn }) =>
      api<FixOut>(`/sites/${siteId}/fixes/${fixId}`, { method: "PATCH", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["fixes"] });
      void qc.invalidateQueries({ queryKey: ["fix"] });
    },
  });
}

export function useApproveFix(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fixId: string) =>
      api<FixOut>(`/sites/${siteId}/fixes/${fixId}/approve`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["fixes"] });
      void qc.invalidateQueries({ queryKey: ["fix"] });
    },
  });
}

export function useRejectFix(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fixId: string) =>
      api<FixOut>(`/sites/${siteId}/fixes/${fixId}/reject`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["fixes"] });
      void qc.invalidateQueries({ queryKey: ["fix"] });
    },
  });
}

export function useDeployFix(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ fixId, body }: { fixId: string; body: FixDeployIn }) =>
      api<FixOut>(`/sites/${siteId}/fixes/${fixId}/deploy`, { method: "POST", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["fixes"] });
      void qc.invalidateQueries({ queryKey: ["fix"] });
    },
  });
}

export function useRollbackFix(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fixId: string) =>
      api<FixOut>(`/sites/${siteId}/fixes/${fixId}/rollback`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["fixes"] });
      void qc.invalidateQueries({ queryKey: ["fix"] });
    },
  });
}

// --- Phase 3: Diagnosis ---

export function useDiagnoses(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["diagnoses", org, siteId],
    queryFn: () => api<DiagnosisOut[]>(`/sites/${siteId}/diagnoses`),
    enabled: !!org && !!siteId,
  });
}

export function useDiagnosis(siteId: string | undefined, diagnosisId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["diagnosis", org, siteId, diagnosisId],
    queryFn: () => api<DiagnosisOut>(`/sites/${siteId}/diagnoses/${diagnosisId}`),
    enabled: !!org && !!siteId && !!diagnosisId,
  });
}

export function useTriggerDiagnosis(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DiagnosisTriggerIn) =>
      api<DiagnosisOut>(`/sites/${siteId}/diagnose`, { method: "POST", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["diagnoses"] });
      void qc.invalidateQueries({ queryKey: ["fixes"] });
    },
  });
}

// --- Phase 3: Verification ---

export function useVerification(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["verification", org, siteId],
    queryFn: () => api<VerificationStatusOut>(`/sites/${siteId}/verification`),
    enabled: !!org && !!siteId,
  });
}

export function useVerifySite(siteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<VerifyAttemptOut>(`/sites/${siteId}/verify`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["verification"] });
      void qc.invalidateQueries({ queryKey: ["site"] });
      void qc.invalidateQueries({ queryKey: ["sites"] });
    },
  });
}

// --- Phase 3: Integrations & API Keys / Webhooks ---

export function useSnippetInfo(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["snippet-info", org, siteId],
    queryFn: () => api<SnippetInfoOut>(`/sites/${siteId}/integrations/snippet`),
    enabled: !!org && !!siteId,
  });
}

export function useApiKeys() {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["api-keys", org],
    queryFn: () => api<ApiKeyOut[]>("/org/api-keys"),
    enabled: !!org,
  });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ApiKeyCreateIn) =>
      api<ApiKeyCreatedOut>("/org/api-keys", { method: "POST", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
}

export function useDeleteApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => api(`/org/api-keys/${keyId}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
}

export function useWebhooks() {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["webhooks", org],
    queryFn: () => api<WebhookOut[]>("/org/webhooks"),
    enabled: !!org,
  });
}

export function useCreateWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WebhookCreateIn) =>
      api<WebhookCreatedOut>("/org/webhooks", { method: "POST", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });
}

export function useDeleteWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (webhookId: string) => api(`/org/webhooks/${webhookId}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });
}

// --- Phase 4: Deep Platform Integrations ---

export function useSiteIntegrations(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["site-integrations", org, siteId],
    queryFn: () => api<SiteIntegrationOut[]>(`/sites/${siteId}/integrations`),
    enabled: !!org && !!siteId,
  });
}

export function useCreateSiteIntegration(siteId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SiteIntegrationCreateIn) =>
      api<SiteIntegrationOut>(`/sites/${siteId}/integrations`, { method: "POST", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["site-integrations"] });
    },
  });
}

export function useUpdateSiteIntegration(siteId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: SiteIntegrationUpdateIn }) =>
      api<SiteIntegrationOut>(`/sites/${siteId}/integrations/${id}`, { method: "PATCH", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["site-integrations"] });
    },
  });
}

export function useDeleteSiteIntegration(siteId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(`/sites/${siteId}/integrations/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["site-integrations"] });
    },
  });
}

export function useTestSiteIntegration(siteId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api<TestConnectionOut>(`/sites/${siteId}/integrations/${id}/test`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["site-integrations"] });
    },
  });
}

export function useGscAuthUrl(siteId: string | undefined, redirectUri?: string) {
  const org = useOrgKey();
  const query = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : "";
  return useQuery({
    queryKey: ["gsc-auth-url", org, siteId, redirectUri],
    queryFn: () =>
      api<GscAuthUrlOut>(`/sites/${siteId}/integrations/google-search-console/auth-url${query}`),
    enabled: !!org && !!siteId,
  });
}

export function useConnectGsc(siteId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: GscConnectIn) =>
      api<SiteIntegrationOut>(`/sites/${siteId}/integrations/google-search-console/connect`, {
        method: "POST",
        body,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["site-integrations"] });
      void qc.invalidateQueries({ queryKey: ["site"] });
      void qc.invalidateQueries({ queryKey: ["verification"] });
    },
  });
}

export function useGscPerformance(siteId: string | undefined, enabled = true) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["gsc-performance", org, siteId],
    queryFn: () =>
      api<GscPerformanceOut>(`/sites/${siteId}/integrations/google-search-console/performance`),
    enabled: !!org && !!siteId && enabled,
  });
}

export function useAudits(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["audits", org, siteId],
    queryFn: () => api<AuditOut[]>(`/sites/${siteId}/audits`),
    enabled: !!org && !!siteId,
  });
}

export function useAudit(siteId: string | undefined, auditId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["audit", org, siteId, auditId],
    queryFn: () => api<AuditOut>(`/sites/${siteId}/audits/${auditId}`),
    enabled: !!org && !!siteId && !!auditId,
  });
}

export function useRunAudit(siteId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body?: AuditTriggerIn) =>
      api<AuditOut>(`/sites/${siteId}/audits`, { method: "POST", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["audits"] });
    },
  });
}

export function useReports(siteId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["reports", org, siteId],
    queryFn: () => api<ReportOut[]>(`/sites/${siteId}/reports`),
    enabled: !!org && !!siteId,
  });
}

export function useReport(siteId: string | undefined, reportId: string | undefined) {
  const org = useOrgKey();
  return useQuery({
    queryKey: ["report", org, siteId, reportId],
    queryFn: () => api<ReportOut>(`/sites/${siteId}/reports/${reportId}`),
    enabled: !!org && !!siteId && !!reportId,
  });
}

export function useGenerateReport(siteId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body?: ReportCreateIn) =>
      api<ReportOut>(`/sites/${siteId}/reports`, { method: "POST", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}

export function useSendTestDigest(siteId: string | undefined) {
  return useMutation({
    mutationFn: (body?: { language?: string }) =>
      api<DigestSendTestOut>(`/sites/${siteId}/reports/digest/send-test`, {
        method: "POST",
        body,
      }),
  });
}
