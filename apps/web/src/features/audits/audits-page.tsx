import { T } from "@/components/ui/t";
import { useSelectedSite } from "@/lib/use-selected-site";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  FileSearch,
  Globe,
  Info,
  Play,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { EmptyState, ErrorState, PageHeader } from "@/components/ui/states";
import type { AuditIssueOut } from "@/lib/api-types";
import { useAudits, useRunAudit, useSites } from "@/lib/queries";

export function AuditsPage() {
  const { t, i18n } = useTranslation("app");
  const isAr = i18n.language === "ar";

  const sites = useSites();
  const [selectedSiteId, setSelectedSiteId] = useSelectedSite();
  const siteId = selectedSiteId;

  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [selectedAuditId, setSelectedAuditId] = useState<string | null>(null);

  const audits = useAudits(siteId);
  const runAudit = useRunAudit(siteId);

  if (sites.isPending) return <PageLoader />;
  if (sites.isError) return <ErrorState error={sites.error} onRetry={() => void sites.refetch()} />;

  if (!sites.data || sites.data.length === 0) {
    return (
      <EmptyState
        icon={Globe}
        title={t("sites.emptyTitle")}
        description={t("sites.emptyBody")}
        action={
          <Button asChild>
            <Link to="/app/onboarding">{t("overview.addSite")}</Link>
          </Button>
        }
      />
    );
  }

  const auditList = audits.data ?? [];
  const currentAudit = selectedAuditId
    ? (auditList.find((a) => a.id === selectedAuditId) ?? auditList[0])
    : auditList[0];

  const handleRunAudit = () => {
    runAudit.mutate(
      {},
      {
        onSuccess: (newAudit) => {
          setSelectedAuditId(newAudit.id);
        },
      },
    );
  };

  const getScoreColor = (score: number) => {
    if (score >= 80)
      return "text-emerald-600 bg-emerald-50 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400";
    if (score >= 60)
      return "text-amber-600 bg-amber-50 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400";
    return "text-rose-600 bg-rose-50 border-rose-200 dark:bg-rose-950/40 dark:text-rose-400";
  };

  const getSeverityBadge = (severity: string, passed: boolean) => {
    if (passed) {
      return (
        <Badge variant="success" className="gap-1">
          <CheckCircle2 className="h-3 w-3" />
          {t("audits.severityPassed")}
        </Badge>
      );
    }
    switch (severity) {
      case "critical":
        return (
          <Badge
            variant="outline"
            className="gap-1 border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
          >
            <ShieldAlert className="h-3 w-3" />
            {t("audits.severityCritical")}
          </Badge>
        );
      case "warning":
        return (
          <Badge variant="warning" className="gap-1">
            <AlertTriangle className="h-3 w-3" />
            {t("audits.severityWarning")}
          </Badge>
        );
      default:
        return (
          <Badge variant="muted" className="gap-1">
            <Info className="h-3 w-3" />
            {t("audits.severityInfo")}
          </Badge>
        );
    }
  };

  // Filter issues
  const rawIssues: AuditIssueOut[] = currentAudit?.issues ?? [];
  const filteredIssues = rawIssues.filter((issue) => {
    if (categoryFilter !== "all" && issue.category !== categoryFilter) return false;
    if (severityFilter === "passed") return issue.passed;
    if (severityFilter === "critical") return !issue.passed && issue.severity === "critical";
    if (severityFilter === "warning") return !issue.passed && issue.severity === "warning";
    if (severityFilter === "info") return !issue.passed && issue.severity === "info";
    return true;
  });

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6">
      {/* Top Header */}
      <PageHeader
        title={t("audits.title")}
        description={t("audits.description")}
        actions={
          <div className="flex flex-wrap items-center gap-3">
            {sites.data.length > 1 && (
              <select
                className="bg-background rounded-md border px-3 py-1.5 text-sm"
                value={siteId}
                onChange={(e) => {
                  setSelectedSiteId(e.target.value);
                  setSelectedAuditId(null);
                }}
              >
                {sites.data.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.domain})
                  </option>
                ))}
              </select>
            )}

            <Button
              onClick={handleRunAudit}
              disabled={runAudit.isPending || currentAudit?.status === "running"}
            >
              {runAudit.isPending || currentAudit?.status === "running" ? (
                <>
                  <RefreshCw className="me-2 h-4 w-4 animate-spin" />
                  {t("audits.runningAudit")}
                </>
              ) : (
                <>
                  <Play className="me-2 h-4 w-4" />
                  {t("audits.runAudit")}
                </>
              )}
            </Button>
          </div>
        }
      />

      {/* Error notification if audit trigger fails */}
      {runAudit.isError && (
        <Alert tone="error">
          <AlertCircle className="h-4 w-4" />
          <p>{(runAudit.error as Error)?.message || t("audits.auditFailed")}</p>
        </Alert>
      )}

      {/* No audits yet */}
      {auditList.length === 0 && !runAudit.isPending ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center p-12 text-center">
            <div className="bg-primary/10 mb-4 rounded-full p-4">
              <FileSearch className="text-primary h-8 w-8" />
            </div>
            <h3 className="text-lg font-semibold">{t("audits.noAuditsTitle")}</h3>
            <p className="text-muted-foreground mt-1 max-w-md text-sm">
              {t("audits.noAuditsDesc")}
            </p>
            <Button onClick={handleRunAudit} className="mt-6" size="lg">
              <Play className="me-2 h-4 w-4" />
              {t("audits.runFirstAudit")}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Audit History Dropdown if multiple audits exist */}
          {auditList.length > 1 && (
            <div className="bg-muted/40 flex items-center justify-between rounded-lg border p-3">
              <div className="text-muted-foreground flex items-center gap-2 text-xs">
                <Clock className="h-4 w-4" />
                <span>{t("audits.auditHistory")}:</span>
              </div>
              <select
                className="bg-background rounded border px-2.5 py-1 text-xs"
                value={currentAudit?.id ?? ""}
                onChange={(e) => setSelectedAuditId(e.target.value)}
              >
                {auditList.map((a) => (
                  <option key={a.id} value={a.id}>
                    {new Date(a.created_at).toLocaleString()} <T k="audits.score" /> {a.score}/100 (
                    {a.status})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Running State Card */}
          {currentAudit?.status === "running" && (
            <Card className="border-indigo-200 bg-indigo-50/50 dark:border-indigo-900 dark:bg-indigo-950/20">
              <CardContent className="flex items-center gap-4 p-6">
                <RefreshCw className="h-6 w-6 animate-spin text-indigo-600" />
                <div>
                  <h4 className="font-semibold text-indigo-950 dark:text-indigo-200">
                    {t("audits.auditInProgress")}
                  </h4>
                  <p className="text-xs text-indigo-800 dark:text-indigo-300">
                    {t("audits.auditCrawlingExplanation")}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Executive Scorecard */}
          {currentAudit && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              {/* Overall Score */}
              <Card className="flex flex-col items-center justify-center p-6 text-center lg:col-span-1">
                <div
                  className={`flex size-24 flex-col items-center justify-center rounded-full border-4 font-bold shadow-sm ${getScoreColor(
                    currentAudit.score,
                  )}`}
                >
                  <span className="text-3xl leading-none">{currentAudit.score}</span>
                  <span className="mt-0.5 text-[10px] font-normal tracking-wider uppercase opacity-80">
                    / 100
                  </span>
                </div>
                <h4 className="mt-3 text-sm font-semibold">{t("audits.overallScore")}</h4>
                <p className="text-muted-foreground mt-0.5 text-xs">
                  {currentAudit.pages_crawled} {t("audits.pagesCrawled")}
                </p>
              </Card>

              {/* Category Breakdown Cards */}
              <Card className="flex flex-col justify-between p-6 lg:col-span-4">
                <div>
                  <div className="mb-4 flex items-center justify-between">
                    <h4 className="text-sm font-semibold">{t("audits.categoryBreakdown")}</h4>
                    <span className="text-muted-foreground text-xs">
                      {new Date(currentAudit.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {/* Technical */}
                    <div className="bg-muted/20 space-y-1.5 rounded-lg border p-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium">{t("audits.catTechnical")}</span>
                        <span className="font-bold">
                          {currentAudit.category_scores.technical ?? 0}%
                        </span>
                      </div>
                      <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
                        <div
                          className="h-full rounded-full bg-indigo-600"
                          style={{ width: `${currentAudit.category_scores.technical ?? 0}%` }}
                        />
                      </div>
                      <p className="text-muted-foreground text-[11px]">
                        {t("audits.weightTechnical")}
                      </p>
                    </div>

                    {/* Content */}
                    <div className="bg-muted/20 space-y-1.5 rounded-lg border p-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium">{t("audits.catContent")}</span>
                        <span className="font-bold">
                          {currentAudit.category_scores.content ?? 0}%
                        </span>
                      </div>
                      <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
                        <div
                          className="h-full rounded-full bg-emerald-600"
                          style={{ width: `${currentAudit.category_scores.content ?? 0}%` }}
                        />
                      </div>
                      <p className="text-muted-foreground text-[11px]">
                        {t("audits.weightContent")}
                      </p>
                    </div>

                    {/* AI Readiness */}
                    <div className="bg-muted/20 space-y-1.5 rounded-lg border p-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium">{t("audits.catAiReadiness")}</span>
                        <span className="font-bold">
                          {currentAudit.category_scores.ai_readiness ?? 0}%
                        </span>
                      </div>
                      <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
                        <div
                          className="h-full rounded-full bg-purple-600"
                          style={{ width: `${currentAudit.category_scores.ai_readiness ?? 0}%` }}
                        />
                      </div>
                      <p className="text-muted-foreground text-[11px]">
                        {t("audits.weightAiReadiness")}
                      </p>
                    </div>

                    {/* Performance */}
                    <div className="bg-muted/20 space-y-1.5 rounded-lg border p-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium">{t("audits.catPerformance")}</span>
                        <span className="font-bold">
                          {currentAudit.category_scores.performance ?? 0}%
                        </span>
                      </div>
                      <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
                        <div
                          className="h-full rounded-full bg-amber-600"
                          style={{ width: `${currentAudit.category_scores.performance ?? 0}%` }}
                        />
                      </div>
                      <p className="text-muted-foreground text-[11px]">
                        {t("audits.weightPerformance")}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Summary Text */}
                <div className="text-muted-foreground mt-4 border-t pt-3 text-xs leading-relaxed">
                  <span className="text-foreground me-1 font-semibold">
                    {t("audits.executiveSummary")}:
                  </span>
                  {isAr && currentAudit.summary_ar ? currentAudit.summary_ar : currentAudit.summary}
                </div>
              </Card>
            </div>
          )}

          {/* Issues and Recommendations Section */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle className="text-base font-semibold">
                    {t("audits.issuesTitle")}
                  </CardTitle>
                  <CardDescription className="text-xs">
                    {t("audits.issuesDesc", { count: rawIssues.length })}
                  </CardDescription>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    className="bg-background rounded border px-2.5 py-1 text-xs"
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                  >
                    <option value="all">{t("audits.allCategories")}</option>
                    <option value="technical">{t("audits.catTechnical")}</option>
                    <option value="content">{t("audits.catContent")}</option>
                    <option value="ai_readiness">{t("audits.catAiReadiness")}</option>
                    <option value="performance">{t("audits.catPerformance")}</option>
                  </select>

                  <select
                    className="bg-background rounded border px-2.5 py-1 text-xs"
                    value={severityFilter}
                    onChange={(e) => setSeverityFilter(e.target.value)}
                  >
                    <option value="all">{t("audits.allSeverities")}</option>
                    <option value="critical">{t("audits.severityCritical")}</option>
                    <option value="warning">{t("audits.severityWarning")}</option>
                    <option value="info">{t("audits.severityInfo")}</option>
                    <option value="passed">{t("audits.severityPassed")}</option>
                  </select>
                </div>
              </div>
            </CardHeader>

            <CardContent className="space-y-3">
              {filteredIssues.length === 0 ? (
                <div className="text-muted-foreground py-8 text-center text-xs">
                  {t("audits.noMatchingIssues")}
                </div>
              ) : (
                filteredIssues.map((issue) => {
                  const issueTitle = isAr && issue.title_ar ? issue.title_ar : issue.title;
                  const issueDesc =
                    isAr && issue.description_ar ? issue.description_ar : issue.description;
                  const issueRec =
                    isAr && issue.recommendation_ar
                      ? issue.recommendation_ar
                      : issue.recommendation;

                  return (
                    <div
                      key={issue.id}
                      className={`rounded-lg border p-4 transition-colors ${
                        issue.passed
                          ? "border-emerald-200/50 bg-emerald-50/20 dark:bg-emerald-950/10"
                          : issue.severity === "critical"
                            ? "border-rose-200/50 bg-rose-50/20 dark:bg-rose-950/10"
                            : "bg-muted/10 border-border"
                      }`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="flex items-center gap-2">
                          {getSeverityBadge(issue.severity, issue.passed)}
                          <span className="text-muted-foreground bg-muted/60 rounded px-2 py-0.5 text-[11px] font-medium tracking-wider uppercase">
                            {issue.category}
                          </span>
                        </div>
                      </div>

                      <h5 className="mt-2 text-sm font-semibold">{issueTitle}</h5>
                      <p className="text-muted-foreground mt-1 text-xs leading-relaxed">
                        {issueDesc}
                      </p>

                      {!issue.passed && issueRec && (
                        <div className="border-primary/20 bg-primary/5 text-primary-950 dark:text-primary-100 mt-3 rounded border p-2.5 text-xs">
                          <span className="font-semibold">{t("audits.recommendation")}: </span>
                          <span>{issueRec}</span>
                        </div>
                      )}

                      {issue.affected_urls && issue.affected_urls.length > 0 && (
                        <div className="text-muted-foreground mt-2 text-[11px]">
                          <span className="font-medium">{t("audits.affectedPages")}: </span>
                          <span className="font-mono">
                            {issue.affected_urls.slice(0, 3).join(", ")}
                          </span>
                          {issue.affected_urls.length > 3 && (
                            <span className="ms-1">
                              +{issue.affected_urls.length - 3} <T k="audits.more" />
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
