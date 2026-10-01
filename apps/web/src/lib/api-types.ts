import type { components } from "./api-types.gen";

type S = components["schemas"];
export type SessionOut = S["SessionOut"];
export type UserOut = S["UserOut"];
export type OrgSummary = S["OrgSummary"];
export type OrgOut = S["OrgOut"];
export type PlanOut = S["PlanOut"];
export type MemberOut = S["MemberOut"];
export type InvitationOut = S["InvitationOut"];
export type SiteOut = S["SiteOut"];
export type SiteCreateIn = S["SiteCreateIn"];
export type SiteUpdateIn = S["SiteUpdateIn"];
export type KeywordIn = S["KeywordIn"];
export type KeywordOut = S["KeywordOut"];
export type PromptIn = S["PromptIn"];
export type PromptOut = S["PromptOut"];
export type AnalyzeOut = S["AnalyzeOut"];
export type SuggestOut = S["SuggestOut"];
export type CompleteIn = S["CompleteIn"];
export type AdminOrgOut = S["AdminOrgOut"];
export type Platform = SiteCreateIn["platform"];
export type RankedKeywordOut = S["RankedKeywordOut"];
export type AiCheckRunOut = S["AiCheckRunOut"];
export type PromptVisibilityOut = S["PromptVisibilityOut"];
export type AiVisibilitySummaryOut = S["AiVisibilitySummaryOut"];
export type CrawlSnapshotOut = S["CrawlSnapshotOut"];
export type SiteOverviewOut = S["SiteOverviewOut"];
export type RankingWinLossOut = S["RankingWinLossOut"];
export type CompetitorShareOut = S["CompetitorShareOut"];
export type FixOut = S["FixOut"] & { external_reference?: string | null };

export type FixUpdateIn = S["FixUpdateIn"];
export type FixDeployIn = S["FixDeployIn"];
export type DiagnosisOut = S["DiagnosisOut"];
export type DiagnosisTriggerIn = S["DiagnosisTriggerIn"];
export type VerificationStatusOut = S["VerificationStatusOut"];
export type VerifyAttemptOut = S["VerifyAttemptOut"];
export type SnippetInfoOut = S["SnippetInfoOut"];
export type ApiKeyOut = S["ApiKeyOut"];
export type ApiKeyCreateIn = S["ApiKeyCreateIn"];
export type ApiKeyCreatedOut = S["ApiKeyCreatedOut"];
export type WebhookOut = S["WebhookOut"];
export type WebhookCreateIn = S["WebhookCreateIn"];

export interface SiteIntegrationOut {
  id: string;
  site_id: string;
  provider: string;
  status: string;
  config: Record<string, unknown>;
  last_synced_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface SiteIntegrationCreateIn {
  provider: string;
  config?: Record<string, unknown>;
  credentials?: Record<string, unknown>;
}

export interface SiteIntegrationUpdateIn {
  status?: string;
  config?: Record<string, unknown>;
  credentials?: Record<string, unknown>;
}

export interface TestConnectionOut {
  ok: boolean;
  message: string;
  details?: Record<string, unknown>;
}

export interface GscAuthUrlOut {
  auth_url: string;
}

export interface GscConnectIn {
  code: string;
  property_url: string;
  redirect_uri: string;
}

export interface GscPerformanceOut {
  property_url: string;
  rows: Array<{
    keys?: string[];
    clicks?: number;
    impressions?: number;
    ctr?: number;
    position?: number;
    [key: string]: unknown;
  }>;
}
