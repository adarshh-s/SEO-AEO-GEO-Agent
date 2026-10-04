import { engineName } from "@/lib/engines";
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  BarChart3,
  Bot,
  Globe,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wrench,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, Navigate } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Jargon } from "@/components/ui/jargon";
import { PageLoader } from "@/components/ui/spinner";
import { SitePicker } from "@/components/site-picker";
import { useSelectedSite } from "@/lib/use-selected-site";
import { ErrorState, PageHeader } from "@/components/ui/states";
import { formatNumber } from "@/lib/i18n";
import { useOrg, useSiteOverview, useSites } from "@/lib/queries";

export function OverviewPage() {
  const { t } = useTranslation("app");
  const sites = useSites();
  const org = useOrg();

  const [siteId] = useSelectedSite();
  const overview = useSiteOverview(siteId);

  if (sites.isPending || org.isPending) return <PageLoader />;
  if (sites.isError) return <ErrorState error={sites.error} onRetry={() => void sites.refetch()} />;
  if (sites.data.length === 0) {
    return sites.isFetching ? <PageLoader /> : <Navigate to="/app/onboarding" replace />;
  }

  const usage = org.data?.usage;
  const overviewData = overview.data;

  const tiles = [
    {
      icon: BarChart3,
      term: "seoScore",
      value: overviewData ? `${formatNumber(overviewData.seo_score)}%` : "—",
      subtext: "Google ranking performance",
    },
    {
      icon: Bot,
      term: "shareOfVoice",
      value: overviewData ? `${formatNumber(overviewData.ai_share_of_voice)}%` : "—",
      subtext: "Mentions across AI engines",
    },
    {
      icon: Globe,
      label: t("overview.sites"),
      value: usage ? formatNumber(usage.sites) : "—",
      subtext: `${usage?.keywords ?? 0} keywords · ${usage?.prompts ?? 0} AI questions`,
    },
    {
      icon: Wrench,
      label: t("overview.fixesWaiting"),
      value: overviewData ? formatNumber(overviewData.fixes_waiting) : "0",
      subtext: "Ready to deploy",
    },
  ];

  const spend = overviewData?.monthly_spend_usd ?? 0;
  const ceiling = overviewData?.monthly_cost_ceiling_usd ?? 0;
  const ratio = overviewData?.spend_ratio ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("overview.title")}
        description={t("overview.description")}
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <SitePicker />
            <Button asChild variant="outline">
              <Link to="/app/onboarding">{t("overview.addSite")}</Link>
            </Button>
          </div>
        }
      />

      {/* Spending ceiling warning if ratio >= 80% */}
      {ratio >= 0.8 && (
        <Alert tone={ratio >= 1.0 ? "error" : "warning"}>
          <div className="flex items-center gap-2">
            <AlertTriangle className="size-4 shrink-0" aria-hidden />
            <span>
              {t("overviewDetails.ceilingWarning", { ratio: Math.round(ratio * 100) })}: $
              {formatNumber(spend)} / ${formatNumber(ceiling)} USD
            </span>
          </div>
        </Alert>
      )}

      {/* Main KPI Tiles */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map(({ icon: Icon, term, label, value, subtext }) => (
          <Card key={term ?? label}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-muted-foreground text-sm font-medium">
                {term ? <Jargon term={term} /> : label}
              </CardTitle>
              <Icon className="text-muted-foreground size-4" aria-hidden />
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{value}</p>
              <p className="text-muted-foreground mt-1 text-xs">{subtext}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* AI Engine Share Breakdown */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Sparkles className="size-4 text-purple-600" aria-hidden />
              {t("overviewDetails.engineBreakdown")}
            </CardTitle>
            <CardDescription>Brand mention share by AI assistant</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {["chatgpt", "gemini", "perplexity", "claude"].map((engine) => {
              const pct = overviewData?.per_engine?.[engine] ?? 0;
              return (
                <div key={engine} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-medium">
                    <span>{engineName(engine)}</span>
                    <span className="text-muted-foreground">{formatNumber(pct)}%</span>
                  </div>
                  <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
                    <div
                      className="bg-primary h-full rounded-full transition-all"
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Wins and Losses */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Ranking Movements</CardTitle>
            <CardDescription>Biggest keyword position gains and drops</CardDescription>
          </CardHeader>
          <CardContent>
            {!overviewData?.ranking_wins.length && !overviewData?.ranking_losses.length ? (
              <p className="text-muted-foreground py-8 text-center text-sm">
                {t("overviewDetails.noChanges")}
              </p>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                {/* Wins */}
                <div className="space-y-2">
                  <h4 className="flex items-center gap-1 text-xs font-semibold text-emerald-600 uppercase">
                    <TrendingUp className="size-3.5" aria-hidden />
                    {t("overviewDetails.rankingWins")}
                  </h4>
                  <div className="space-y-2">
                    {overviewData.ranking_wins.map((w) => (
                      <div
                        key={w.keyword_id}
                        className="bg-muted/40 flex items-center justify-between rounded p-2 text-xs"
                      >
                        <span className="max-w-[140px] truncate font-medium">{w.keyword}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">#{w.current_position}</span>
                          <span className="flex items-center font-semibold text-emerald-600">
                            <ArrowUp className="me-0.5 size-3" aria-hidden />+{w.change}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Losses */}
                <div className="space-y-2">
                  <h4 className="flex items-center gap-1 text-xs font-semibold text-rose-600 uppercase">
                    <TrendingDown className="size-3.5" aria-hidden />
                    {t("overviewDetails.rankingLosses")}
                  </h4>
                  <div className="space-y-2">
                    {overviewData.ranking_losses.map((l) => (
                      <div
                        key={l.keyword_id}
                        className="bg-muted/40 flex items-center justify-between rounded p-2 text-xs"
                      >
                        <span className="max-w-[140px] truncate font-medium">{l.keyword}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">#{l.current_position}</span>
                          <span className="flex items-center font-semibold text-rose-600">
                            <ArrowDown className="me-0.5 size-3" aria-hidden />
                            {l.change}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Monthly Budget Tracker Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle className="text-base font-semibold">
              {t("overviewDetails.monthlyUsage")}
            </CardTitle>
            <CardDescription>Real-time cost tracking against your monthly limit</CardDescription>
          </div>
          <Badge variant={ratio >= 1.0 ? "warning" : ratio >= 0.8 ? "outline" : "muted"}>
            ${formatNumber(spend)} / ${formatNumber(ceiling)} USD
          </Badge>
        </CardHeader>
        <CardContent>
          <div className="bg-muted h-2.5 w-full overflow-hidden rounded-full">
            <div
              className={`h-full rounded-full transition-all ${
                ratio >= 1.0 ? "bg-rose-600" : ratio >= 0.8 ? "bg-amber-500" : "bg-primary"
              }`}
              style={{ width: `${Math.min(ratio * 100, 100)}%` }}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
