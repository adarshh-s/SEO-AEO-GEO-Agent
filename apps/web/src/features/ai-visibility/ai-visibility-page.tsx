import {
  Bot,
  CheckCircle2,
  ExternalLink,
  Eye,
  RefreshCw,
  TrendingUp,
  X,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { EmptyState, ErrorState, PageHeader } from "@/components/ui/states";
import type { AiVisibilitySummaryOut, PromptVisibilityOut } from "@/lib/api-types";
import { formatNumber } from "@/lib/i18n";
import {
  useAiVisibility,
  usePromptRuns,
  useSites,
  useTriggerAllPromptChecks,
  useTriggerPromptCheck,
} from "@/lib/queries";

export function AiVisibilityPage() {
  const { t } = useTranslation("app");
  const tc = useTranslation().t;
  const sites = useSites();

  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [selectedLang, setSelectedLang] = useState<string>("all");
  const [inspectPrompt, setInspectPrompt] = useState<PromptVisibilityOut | null>(null);

  const siteId = selectedSiteId ?? sites.data?.[0]?.id;
  const currentSite = sites.data?.find((s) => s.id === siteId);

  const aiVisibility = useAiVisibility(siteId);
  const triggerAll = useTriggerAllPromptChecks(siteId ?? "");
  const triggerCheck = useTriggerPromptCheck(siteId ?? "");

  if (sites.isPending) return <PageLoader />;
  if (sites.isError) return <ErrorState error={sites.error} onRetry={() => void sites.refetch()} />;

  if (!sites.data || sites.data.length === 0) {
    return (
      <EmptyState
        icon={Bot}
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

  const data = aiVisibility.data as AiVisibilitySummaryOut | undefined;
  const prompts = data?.prompts ?? [];
  const filteredPrompts =
    selectedLang === "all" ? prompts : prompts.filter((p) => p.language === selectedLang);

  const siteLanguages = currentSite
    ? [currentSite.primary_language, ...currentSite.additional_languages]
    : [];

  const engines = ["chatgpt", "gemini", "perplexity", "claude"];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("aiVisibility.title")}
        description={t("aiVisibility.description")}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {sites.data.length > 1 && (
              <select
                className="border-input bg-background rounded-md border px-3 py-1.5 text-sm"
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
            <Button
              variant="outline"
              disabled={triggerAll.isPending}
              onClick={() => triggerAll.mutate()}
            >
              <RefreshCw
                className={`me-2 size-4 ${triggerAll.isPending ? "animate-spin" : ""}`}
                aria-hidden
              />
              {triggerAll.isPending ? t("keywords.checking") : t("aiVisibility.checkAll")}
            </Button>
          </div>
        }
      />

      {/* Summary KPI Tiles */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-muted-foreground text-sm font-medium">
              {t("aiVisibility.overallSoV")}
            </CardTitle>
            <TrendingUp className="text-muted-foreground size-4" aria-hidden />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">
              {data ? `${formatNumber(data.overall_share_of_voice)}%` : "—"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-muted-foreground text-sm font-medium">
              {t("aiVisibility.mentionRate")}
            </CardTitle>
            <Bot className="text-muted-foreground size-4" aria-hidden />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">
              {data ? `${formatNumber(data.brand_mention_rate)}%` : "—"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-muted-foreground text-sm font-medium">
              {t("aiVisibility.citationRate")}
            </CardTitle>
            <ExternalLink className="text-muted-foreground size-4" aria-hidden />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">
              {data ? `${formatNumber(data.citation_rate)}%` : "—"}
            </p>
          </CardContent>
        </Card>
      </div>

      {siteLanguages.length > 1 && (
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={selectedLang === "all" ? "default" : "outline"}
            onClick={() => setSelectedLang("all")}
          >
            {t("keywords.allLanguages")}
          </Button>
          {siteLanguages.map((l) => (
            <Button
              key={l}
              size="sm"
              variant={selectedLang === l ? "default" : "outline"}
              onClick={() => setSelectedLang(l)}
            >
              {tc(`languageNames.${l}`)}
            </Button>
          ))}
        </div>
      )}

      {aiVisibility.isPending ? (
        <PageLoader />
      ) : aiVisibility.isError ? (
        <ErrorState error={aiVisibility.error} onRetry={() => void aiVisibility.refetch()} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main Matrix: Prompts x Engines (2 cols on lg) */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold">
                  {t("sections.aiVisibility.title")}
                </CardTitle>
                <CardDescription>{t("sections.aiVisibility.description")}</CardDescription>
              </CardHeader>
              <div className="overflow-x-auto">
                <table className="w-full text-start text-sm">
                  <thead className="bg-muted/50 border-y text-xs font-medium uppercase">
                    <tr>
                      <th className="px-4 py-3 text-start">{t("aiVisibility.prompt")}</th>
                      {engines.map((e) => (
                        <th key={e} className="px-3 py-3 text-center capitalize">
                          {e}
                        </th>
                      ))}
                      <th className="px-4 py-3 text-end"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {filteredPrompts.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="text-muted-foreground py-8 text-center text-sm">
                          {t("sections.aiVisibility.empty")}
                        </td>
                      </tr>
                    ) : (
                      filteredPrompts.map((p) => (
                        <tr key={p.id} className="hover:bg-muted/30 transition-colors">
                          <td className="max-w-[240px] px-4 py-3">
                            <div className="text-foreground font-medium">{p.prompt_text}</div>
                            <div className="text-muted-foreground flex items-center gap-1.5 text-xs">
                              <span>{tc(`languageNames.${p.language}`)}</span>
                              <span>·</span>
                              <Badge variant="outline" className="text-[10px]">
                                {p.intent}
                              </Badge>
                            </div>
                          </td>
                          {engines.map((e) => {
                            const st = p.engines_status?.[e];
                            return (
                              <td key={e} className="px-3 py-3 text-center">
                                {st ? (
                                  <div className="flex flex-col items-center gap-1">
                                    {st.mentioned ? (
                                      <CheckCircle2
                                        className="size-4 text-emerald-600"
                                        aria-label={t("aiVisibility.mentioned")}
                                      />
                                    ) : (
                                      <XCircle
                                        className="size-4 text-zinc-300 dark:text-zinc-600"
                                        aria-label={t("aiVisibility.notMentioned")}
                                      />
                                    )}
                                    {st.cited && (
                                      <Badge
                                        variant="default"
                                        className="bg-purple-600 px-1.5 py-0 text-[9px] text-white"
                                      >
                                        {t("aiVisibility.cited")}
                                      </Badge>
                                    )}
                                  </div>
                                ) : (
                                  <span className="text-muted-foreground text-xs">—</span>
                                )}
                              </td>
                            );
                          })}
                          <td className="px-4 py-3 text-end">
                            <div className="flex items-center justify-end gap-1">
                              <Button size="sm" variant="ghost" onClick={() => setInspectPrompt(p)}>
                                <Eye className="size-3.5" aria-hidden />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={triggerCheck.isPending}
                                onClick={() => triggerCheck.mutate(p.id)}
                              >
                                <RefreshCw
                                  className={`size-3.5 ${triggerCheck.isPending ? "animate-spin" : ""}`}
                                  aria-hidden
                                />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          {/* Competitor Leaderboard */}
          <div>
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold">
                  {t("aiVisibility.leaderboard")}
                </CardTitle>
                <CardDescription>Competitors most frequently cited in answers</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {!data?.competitor_leaderboard || data.competitor_leaderboard.length === 0 ? (
                  <p className="text-muted-foreground text-sm">
                    No competitor mentions recorded yet.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {data.competitor_leaderboard.map((c, i) => (
                      <div key={c.domain} className="space-y-1">
                        <div className="flex items-center justify-between text-xs font-medium">
                          <span className="flex items-center gap-1.5 truncate">
                            <span className="text-muted-foreground">{i + 1}.</span>
                            <span className="truncate">{c.domain}</span>
                          </span>
                          <span className="text-muted-foreground">
                            {formatNumber(c.share_pct)}%
                          </span>
                        </div>
                        <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
                          <div
                            className="bg-primary h-full rounded-full"
                            style={{ width: `${Math.min(c.share_pct, 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Answer Inspection Dialog */}
      {inspectPrompt && siteId && (
        <InspectAnswersDialog
          siteId={siteId}
          prompt={inspectPrompt}
          onClose={() => setInspectPrompt(null)}
        />
      )}
    </div>
  );
}

function InspectAnswersDialog({
  siteId,
  prompt,
  onClose,
}: {
  siteId: string;
  prompt: PromptVisibilityOut;
  onClose: () => void;
}) {
  const { t } = useTranslation("app");
  const runs = usePromptRuns(siteId, prompt.id);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-background max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-lg border shadow-xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold">{t("aiVisibility.rawAnswers")}</h2>
            <p className="text-muted-foreground text-sm">{prompt.prompt_text}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="size-4" aria-hidden />
          </Button>
        </div>

        <div className="space-y-4 p-6">
          {runs.isPending ? (
            <PageLoader />
          ) : runs.isError ? (
            <ErrorState error={runs.error} onRetry={() => void runs.refetch()} />
          ) : runs.data.length === 0 ? (
            <p className="text-muted-foreground text-sm">{t("aiVisibility.noRuns")}</p>
          ) : (
            runs.data.map((r) => (
              <div key={r.id} className="border-muted bg-muted/20 space-y-2 rounded-md border p-4">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <Badge variant="default" className="capitalize">
                      {r.engine}
                    </Badge>
                    <span className="text-muted-foreground">{r.model}</span>
                  </div>
                  <Badge variant={r.brand_mentioned ? "default" : "outline"}>
                    {r.brand_mentioned
                      ? t("aiVisibility.mentioned")
                      : t("aiVisibility.notMentioned")}
                  </Badge>
                </div>
                <div className="bg-background text-foreground rounded border p-3 text-xs leading-relaxed whitespace-pre-wrap">
                  {r.raw_answer}
                </div>
                {r.cited_urls.length > 0 && (
                  <div className="text-xs">
                    <span className="text-muted-foreground font-medium">
                      {t("aiVisibility.citedLinks")}:{" "}
                    </span>
                    <ul className="mt-1 list-disc space-y-0.5 ps-4">
                      {r.cited_urls.map((u) => (
                        <li key={u} className="truncate">
                          <a
                            href={u}
                            target="_blank"
                            rel="noreferrer"
                            className="text-primary hover:underline"
                          >
                            {u}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
