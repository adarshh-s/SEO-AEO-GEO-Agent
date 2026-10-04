import { SUPPORTED_LANGUAGES } from "@/lib/i18n";
import { useSelectedSite } from "@/lib/use-selected-site";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  FileDown,
  FileText,
  Globe,
  Mail,
  Plus,
  RefreshCw,
  Send,
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
import { useGenerateReport, useReports, useSendTestDigest, useSites } from "@/lib/queries";
import { useSession } from "@/stores/session";

export function ReportsPage() {
  const { t, i18n } = useTranslation("app");
  const isAr = i18n.language === "ar";
  const user = useSession((s) => s.user);

  const sites = useSites();
  const [selectedSiteId, setSelectedSiteId] = useSelectedSite();
  const siteId = selectedSiteId;

  const [reportLang, setReportLang] = useState<string>(isAr ? "ar" : "en");
  const [digestLang, setDigestLang] = useState<string>(isAr ? "ar" : "en");
  const [digestSuccess, setDigestSuccess] = useState<string | null>(null);

  const reports = useReports(siteId);
  const generateReport = useGenerateReport(siteId);
  const sendTestDigest = useSendTestDigest(siteId);

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

  const reportList = reports.data ?? [];

  const handleGenerateReport = () => {
    generateReport.mutate({ language: reportLang });
  };

  const handleSendTestDigest = () => {
    setDigestSuccess(null);
    sendTestDigest.mutate(
      { language: digestLang },
      {
        onSuccess: (data) => {
          setDigestSuccess(data.message || `Test digest sent to ${data.recipient}`);
          setTimeout(() => setDigestSuccess(null), 6000);
        },
      },
    );
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6">
      {/* Top Header */}
      <PageHeader
        title={t("reports.title")}
        description={t("reports.description")}
        actions={
          <div className="flex flex-wrap items-center gap-3">
            {sites.data.length > 1 && (
              <select
                className="bg-background rounded-md border px-3 py-1.5 text-sm"
                value={siteId}
                onChange={(e) => setSelectedSiteId(e.target.value)}
              >
                {sites.data.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.domain})
                  </option>
                ))}
              </select>
            )}

            <div className="flex items-center gap-2">
              <select
                className="bg-background rounded-md border px-2.5 py-1.5 text-xs"
                value={reportLang}
                onChange={(e) => setReportLang(e.target.value)}
              >
                <option value="en">{t("reports.english_pdf", { ns: "ui" })}</option>
                {SUPPORTED_LANGUAGES.includes("ar") && (
                  <option value="ar">{t("reports.pdf", { ns: "ui" })}</option>
                )}
              </select>

              <Button onClick={handleGenerateReport} disabled={generateReport.isPending}>
                {generateReport.isPending ? (
                  <>
                    <RefreshCw className="me-2 h-4 w-4 animate-spin" />
                    {t("reports.generating")}
                  </>
                ) : (
                  <>
                    <FileDown className="me-2 h-4 w-4" />
                    {t("reports.generatePdf")}
                  </>
                )}
              </Button>
            </div>
          </div>
        }
      />

      {/* Errors */}
      {generateReport.isError && (
        <Alert tone="error">
          <AlertCircle className="h-4 w-4" />
          <p>{(generateReport.error as Error)?.message || t("reports.generateFailed")}</p>
        </Alert>
      )}

      {/* Section 1: Executive PDF Reports */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base font-semibold">
                {t("reports.pdfReportsTitle")}
              </CardTitle>
              <CardDescription className="text-xs">{t("reports.pdfReportsDesc")}</CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {reportList.length === 0 ? (
            <div className="py-10 text-center">
              <FileText className="text-muted-foreground/60 mx-auto mb-2 h-8 w-8" />
              <p className="text-sm font-medium">{t("reports.noReportsYet")}</p>
              <p className="text-muted-foreground mx-auto mt-1 max-w-sm text-xs">
                {t("reports.noReportsDesc")}
              </p>
              <Button onClick={handleGenerateReport} variant="outline" size="sm" className="mt-4">
                <Plus className="me-1 h-3.5 w-3.5" />
                {t("reports.generateFirstPdf")}
              </Button>
            </div>
          ) : (
            <div className="divide-border/60 divide-y">
              {reportList.map((r) => (
                <div
                  key={r.id}
                  className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-semibold">{r.title}</h4>
                      <Badge variant="outline" className="text-[10px] font-bold uppercase">
                        {r.language}
                      </Badge>
                      <Badge variant="success" className="text-[10px] capitalize">
                        {r.status}
                      </Badge>
                    </div>
                    <p className="text-muted-foreground flex items-center gap-1.5 text-xs">
                      <Clock className="h-3 w-3" />
                      {new Date(r.created_at).toLocaleString()}
                    </p>
                  </div>

                  <Button variant="outline" size="sm" asChild className="h-8 shrink-0 text-xs">
                    <a href={`/api/sites/${siteId}/reports/${r.id}/download`} download>
                      <Download className="me-1.5 h-3.5 w-3.5" />
                      {t("reports.downloadPdf")}
                    </a>
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 2: Automated Weekly Digest */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-indigo-600" />
            <CardTitle className="text-base font-semibold">{t("reports.digestTitle")}</CardTitle>
          </div>
          <CardDescription className="text-xs">{t("reports.digestDesc")}</CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {digestSuccess && (
            <Alert tone="success">
              <CheckCircle2 className="h-4 w-4" />
              <p>{digestSuccess}</p>
            </Alert>
          )}

          {sendTestDigest.isError && (
            <Alert tone="error">
              <AlertCircle className="h-4 w-4" />
              <p>{(sendTestDigest.error as Error)?.message || t("reports.sendDigestFailed")}</p>
            </Alert>
          )}

          <div className="bg-muted/20 space-y-3 rounded-lg border p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h5 className="text-foreground text-xs font-semibold">
                  {t("reports.digestSchedule")}
                </h5>
                <p className="text-muted-foreground text-xs">{t("reports.digestScheduleDetail")}</p>
              </div>

              <div className="flex items-center gap-2">
                <select
                  className="bg-background rounded border px-2.5 py-1 text-xs"
                  value={digestLang}
                  onChange={(e) => setDigestLang(e.target.value)}
                >
                  <option value="en">{t("reports.english_digest", { ns: "ui" })}</option>
                  {SUPPORTED_LANGUAGES.includes("ar") && (
                    <option value="ar">الملخص بالعربية</option>
                  )}
                </select>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSendTestDigest}
                  disabled={sendTestDigest.isPending}
                  className="h-8 text-xs"
                >
                  {sendTestDigest.isPending ? (
                    <>
                      <RefreshCw className="me-1.5 h-3.5 w-3.5 animate-spin" />
                      {t("reports.sendingDigest")}
                    </>
                  ) : (
                    <>
                      <Send className="me-1.5 h-3.5 w-3.5" />
                      {t("reports.sendTestDigest")}
                    </>
                  )}
                </Button>
              </div>
            </div>

            <div className="text-muted-foreground border-t pt-2 text-[11px]">
              <span>
                {t("reports.digestRecipientNotice", { email: user?.email ?? "your email" })}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
