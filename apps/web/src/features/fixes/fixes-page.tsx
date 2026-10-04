import { T } from "@/components/ui/t";
import { useSelectedSite } from "@/lib/use-selected-site";
import {
  Check,
  CheckCircle2,
  Code,
  Copy,
  Edit3,
  ExternalLink,
  FileText,
  Heading,
  HelpCircle,
  RotateCcw,
  UploadCloud,
  Wrench,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PageLoader } from "@/components/ui/spinner";
import { EmptyState, ErrorState, PageHeader } from "@/components/ui/states";
import type { FixOut } from "@/lib/api-types";
import {
  useApproveFix,
  useDeployFix,
  useFixes,
  useRejectFix,
  useRollbackFix,
  useSites,
  useUpdateFix,
} from "@/lib/queries";
import { useSession } from "@/stores/session";

export function FixesPage() {
  const { t } = useTranslation("app");
  const user = useSession((s) => s.user);
  const isEmailVerified = user?.email_verified ?? false;

  const sites = useSites();
  const [selectedSiteId, setSelectedSiteId] = useSelectedSite();
  const siteId = selectedSiteId;

  const [statusFilter, setStatusFilter] = useState<string>("proposed");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [langFilter, setLangFilter] = useState<string>("all");

  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [editingFix, setEditingFix] = useState<FixOut | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editPayloadJson, setEditPayloadJson] = useState("");

  const fixes = useFixes(siteId, {
    status: statusFilter,
    type: typeFilter,
    language: langFilter,
  });

  const approveFix = useApproveFix(siteId ?? "");
  const rejectFix = useRejectFix(siteId ?? "");
  const deployFix = useDeployFix(siteId ?? "");
  const rollbackFix = useRollbackFix(siteId ?? "");
  const updateFix = useUpdateFix(siteId ?? "");

  if (sites.isPending) return <PageLoader />;
  if (sites.isError) return <ErrorState error={sites.error} onRetry={() => void sites.refetch()} />;

  if (!sites.data || sites.data.length === 0) {
    return (
      <EmptyState
        icon={Wrench}
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

  const items = fixes.data ?? [];

  const handleCopy = (id: string, text: string) => {
    void navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleOpenEdit = (fix: FixOut) => {
    setEditingFix(fix);
    setEditTitle(fix.title);
    setEditPayloadJson(JSON.stringify(fix.payload, null, 2));
  };

  const handleSaveEdit = () => {
    if (!editingFix) return;
    try {
      const parsed = JSON.parse(editPayloadJson) as Record<string, unknown>;
      updateFix.mutate(
        {
          fixId: editingFix.id,
          body: { title: editTitle, payload: parsed },
        },
        {
          onSuccess: () => setEditingFix(null),
        },
      );
    } catch {
      alert("Invalid JSON format in payload");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader title={t("fixes.title")} description={t("fixes.description")} />

        {sites.data.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-sm font-medium">
              {t("overview.sites")}:
            </span>
            <select
              value={siteId}
              onChange={(e) => setSelectedSiteId(e.target.value)}
              className="border-input bg-background focus-visible:ring-ring rounded-md border px-3 py-1.5 text-sm focus-visible:ring-2 focus-visible:outline-none"
            >
              {sites.data.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name || s.domain}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {!isEmailVerified && (
        <Alert tone="warning">
          <p className="font-semibold">{t("fixes.emailVerificationRequired")}</p>
          <p>
            <Link to="/app/settings" className="font-medium underline">
              <T k="fixes.go_to_settings_to_verify_your_email" />
            </Link>{" "}
            <T k="fixes.before_approving_or_deploying_fixes_to_y" />
          </p>
        </Alert>
      )}

      {/* Filter Tabs */}
      <div className="border-border bg-card flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3">
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { key: "proposed", label: t("fixes.proposed") },
            { key: "approved", label: t("fixes.approved") },
            { key: "deployed", label: t("fixes.deployed") },
            { key: "rejected", label: t("fixes.rejected") },
            { key: "rolled_back", label: t("fixes.rolledBack") },
            { key: "all", label: t("fixes.allStatus") },
          ].map((tab) => (
            <Button
              key={tab.key}
              variant={statusFilter === tab.key ? "default" : "ghost"}
              size="sm"
              onClick={() => setStatusFilter(tab.key)}
            >
              {tab.label}
            </Button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border-input bg-background rounded-md border px-2.5 py-1 text-xs"
          >
            <option value="all">{t("fixes.allTypes")}</option>
            <option value="schema">{t("fixes.schema")}</option>
            <option value="meta">{t("fixes.meta")}</option>
            <option value="faq">{t("fixes.faq")}</option>
            <option value="content_block">{t("fixes.contentBlock")}</option>
          </select>

          {/* Language Filter */}
          <select
            value={langFilter}
            onChange={(e) => setLangFilter(e.target.value)}
            className="border-input bg-background rounded-md border px-2.5 py-1 text-xs"
          >
            <option value="all">{t("keywords.allLanguages")}</option>
            <option value="en">{t("fixes.english_en", { ns: "ui" })}</option>
            <option value="ar">{t("fixes.ar", { ns: "ui" })}</option>
          </select>
        </div>
      </div>

      {fixes.isPending && <PageLoader />}
      {fixes.isError && <ErrorState error={fixes.error} onRetry={() => void fixes.refetch()} />}

      {!fixes.isPending && !fixes.isError && items.length === 0 && (
        <Card className="p-8 text-center">
          <Wrench className="text-muted-foreground mx-auto mb-3 h-8 w-8" />
          <h3 className="text-base font-semibold">{t("fixes.empty")}</h3>
          <p className="text-muted-foreground mt-1 text-sm">{t("sections.fixes.empty")}</p>
        </Card>
      )}

      {/* Fix Cards List */}
      <div className="space-y-4">
        {items.map((fix) => (
          <Card key={fix.id} className="overflow-hidden">
            <CardHeader className="bg-muted/30 pb-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    variant={
                      fix.status === "deployed"
                        ? "success"
                        : fix.status === "approved"
                          ? "default"
                          : fix.status === "rejected"
                            ? "outline"
                            : fix.status === "rolled_back"
                              ? "muted"
                              : "warning"
                    }
                  >
                    {fix.status}
                  </Badge>

                  <Badge variant="outline" className="flex items-center gap-1">
                    {fix.type === "schema" && <Code className="h-3 w-3" />}
                    {fix.type === "meta" && <Heading className="h-3 w-3" />}
                    {fix.type === "faq" && <HelpCircle className="h-3 w-3" />}
                    {fix.type === "content_block" && <FileText className="h-3 w-3" />}
                    <span>{fix.type}</span>
                  </Badge>

                  <Badge variant="muted" className="text-[10px] uppercase">
                    {fix.language}
                  </Badge>

                  <Badge variant="outline" className="text-[10px]">
                    {fix.recommended_delivery}
                  </Badge>
                </div>

                <a
                  href={fix.target_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-muted-foreground hover:text-foreground flex max-w-[280px] items-center gap-1 truncate text-xs"
                >
                  <span className="truncate">{fix.target_url}</span>
                  <ExternalLink className="h-3 w-3 shrink-0" />
                </a>
              </div>

              <CardTitle className="mt-2 text-base font-semibold">{fix.title}</CardTitle>
              {fix.description && (
                <CardDescription className="text-xs whitespace-pre-line">
                  {fix.description}
                </CardDescription>
              )}
            </CardHeader>

            <CardContent className="space-y-4 pt-4">
              {/* Fix Content Rendering by Type */}
              {fix.type === "schema" && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground text-xs font-semibold">
                      <T k="fixes.json_ld_schema_markup" />
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() =>
                        handleCopy(
                          fix.id,
                          JSON.stringify(fix.payload["json_ld"] ?? fix.payload, null, 2),
                        )
                      }
                    >
                      {copiedId === fix.id ? (
                        <>
                          <Check className="me-1 h-3 w-3 text-emerald-600" />
                          {t("fixes.copied")}
                        </>
                      ) : (
                        <>
                          <Copy className="me-1 h-3 w-3" />
                          {t("fixes.copySchema")}
                        </>
                      )}
                    </Button>
                  </div>
                  <pre className="border-border bg-muted/50 max-h-48 overflow-auto rounded-md border p-3 font-mono text-xs">
                    {JSON.stringify(fix.payload["json_ld"] ?? fix.payload, null, 2)}
                  </pre>
                </div>
              )}

              {fix.type === "meta" && (
                <div className="space-y-3">
                  <span className="text-muted-foreground text-xs font-semibold">
                    <T k="fixes.google_search_preview" />
                  </span>
                  <div className="border-border bg-card rounded-md border p-3 shadow-xs">
                    <div className="truncate text-xs text-emerald-700 dark:text-emerald-500">
                      {fix.target_url}
                    </div>
                    <div className="cursor-pointer text-sm font-medium text-blue-700 hover:underline dark:text-blue-400">
                      {String(fix.payload["title"] ?? "")}
                    </div>
                    <div className="text-muted-foreground mt-1 line-clamp-2 text-xs leading-relaxed">
                      {String(fix.payload["meta_description"] ?? "")}
                    </div>
                  </div>
                </div>
              )}

              {fix.type === "faq" && (
                <div className="space-y-2">
                  <span className="text-muted-foreground text-xs font-semibold">
                    <T k="fixes.faq_accordion_items" />
                  </span>
                  <div className="border-border divide-border divide-y rounded-md border">
                    {Array.isArray(fix.payload["faqs"]) ? (
                      (fix.payload["faqs"] as Array<{ question: string; answer: string }>).map(
                        (faq, idx) => (
                          <div key={idx} className="p-3 text-xs">
                            <p className="text-foreground font-semibold">{faq.question}</p>
                            <p className="text-muted-foreground mt-1 leading-relaxed">
                              {faq.answer}
                            </p>
                          </div>
                        ),
                      )
                    ) : (
                      <pre className="p-3 font-mono text-xs">
                        {JSON.stringify(fix.payload, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              )}

              {fix.type === "content_block" && (
                <div className="space-y-2">
                  <span className="text-muted-foreground text-xs font-semibold">
                    {t("fixes.rendered")}
                  </span>
                  <div
                    className="fix-preview border-border bg-muted/20 rounded-md border p-3 text-xs leading-relaxed"
                    dir={fix.language === "ar" ? "rtl" : "ltr"}
                    dangerouslySetInnerHTML={{ __html: String(fix.payload["html"] ?? "") }}
                  />
                </div>
              )}

              {fix.deployed_via && (
                <div className="text-muted-foreground flex flex-wrap items-center gap-1.5 text-xs">
                  <UploadCloud className="h-3.5 w-3.5 text-emerald-600" />
                  <span>{t("fixes.deployedVia", { method: fix.deployed_via })}</span>
                  {fix.external_reference && (
                    <span className="ms-2 inline-flex items-center gap-1">
                      •
                      {fix.external_reference.startsWith("http") ? (
                        <a
                          href={fix.external_reference}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary inline-flex items-center gap-1 font-mono hover:underline"
                        >
                          <span>{fix.external_reference}</span>
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        <span className="text-muted-foreground/90 font-mono">
                          {fix.external_reference}
                        </span>
                      )}
                    </span>
                  )}
                  {fix.previous_state && (
                    <span className="text-muted-foreground/80 ms-2">
                      • {t("fixes.previousStateSaved")}
                    </span>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="border-border/60 flex flex-wrap items-center justify-between gap-2 border-t pt-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleOpenEdit(fix)}
                  className="h-8 text-xs"
                >
                  <Edit3 className="me-1 h-3 w-3" />
                  {t("fixes.edit")}
                </Button>

                <div className="flex items-center gap-2">
                  {fix.status === "proposed" && (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => rejectFix.mutate(fix.id)}
                        disabled={rejectFix.isPending}
                        className="text-destructive hover:bg-destructive/10 h-8 text-xs"
                      >
                        <XCircle className="me-1 h-3.5 w-3.5" />
                        {t("fixes.reject")}
                      </Button>
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => approveFix.mutate(fix.id)}
                        disabled={approveFix.isPending || !isEmailVerified}
                        className="h-8 bg-emerald-600 text-xs text-white hover:bg-emerald-700"
                      >
                        <CheckCircle2 className="me-1 h-3.5 w-3.5" />
                        {t("fixes.approve")}
                      </Button>
                    </>
                  )}

                  {fix.status === "approved" && (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => rejectFix.mutate(fix.id)}
                        disabled={rejectFix.isPending}
                        className="text-destructive hover:bg-destructive/10 h-8 text-xs"
                      >
                        <XCircle className="me-1 h-3.5 w-3.5" />
                        {t("fixes.reject")}
                      </Button>
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() =>
                          deployFix.mutate({
                            fixId: fix.id,
                            body: { deployed_via: fix.recommended_delivery },
                          })
                        }
                        disabled={deployFix.isPending || !isEmailVerified}
                        className="h-8 text-xs"
                      >
                        <UploadCloud className="me-1 h-3.5 w-3.5" />
                        {t("fixes.deploy")}
                      </Button>
                    </>
                  )}

                  {fix.status === "deployed" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => rollbackFix.mutate(fix.id)}
                      disabled={rollbackFix.isPending}
                      className="h-8 text-xs text-amber-700 hover:bg-amber-50 dark:text-amber-400 dark:hover:bg-amber-950/30"
                    >
                      <RotateCcw className="me-1 h-3.5 w-3.5" />
                      {t("fixes.rollback")}
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Edit Modal Dialog */}
      {editingFix && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
          <Card className="w-full max-w-lg shadow-xl">
            <CardHeader>
              <CardTitle className="text-base">{t("fixes.edit")}</CardTitle>
              <CardDescription className="text-xs">{editingFix.target_url}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-muted-foreground text-xs font-semibold">
                  <T k="fixes.title" />
                </label>
                <Input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="mt-1 text-sm"
                />
              </div>
              <div>
                <label className="text-muted-foreground text-xs font-semibold">
                  <T k="fixes.payload_json" />
                </label>
                <textarea
                  rows={8}
                  value={editPayloadJson}
                  onChange={(e) => setEditPayloadJson(e.target.value)}
                  className="border-input bg-background focus-visible:ring-ring mt-1 w-full rounded-md border p-2 font-mono text-xs focus-visible:ring-2 focus-visible:outline-none"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="ghost" size="sm" onClick={() => setEditingFix(null)}>
                  <T k="fixes.cancel" />
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleSaveEdit}
                  disabled={updateFix.isPending}
                >
                  <T k="fixes.save_changes" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
