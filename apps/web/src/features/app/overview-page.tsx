import { BarChart3, Bot, Globe, Wrench } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, Navigate } from "react-router";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Jargon } from "@/components/ui/jargon";
import { PageLoader } from "@/components/ui/spinner";
import { ErrorState, PageHeader } from "@/components/ui/states";
import { formatNumber } from "@/lib/i18n";
import { useOrg, useSites } from "@/lib/queries";

export function OverviewPage() {
  const { t } = useTranslation("app");
  const sites = useSites();
  const org = useOrg();
  if (sites.isPending || org.isPending) return <PageLoader />;
  if (sites.isError) return <ErrorState error={sites.error} onRetry={() => void sites.refetch()} />;
  if (sites.data.length === 0) {
    // Cached data may be stale (e.g. right after onboarding): wait for the refetch.
    return sites.isFetching ? <PageLoader /> : <Navigate to="/app/onboarding" replace />;
  }
  const usage = org.data?.usage;
  const tiles = [
    { icon: BarChart3, term: "seoScore", value: "—" },
    { icon: Bot, term: "shareOfVoice", value: "—" },
    { icon: Globe, label: t("overview.sites"), value: usage ? formatNumber(usage.sites) : "—" },
    { icon: Wrench, label: t("overview.fixesWaiting"), value: "—" },
  ];
  return (
    <>
      <PageHeader
        title={t("overview.title")}
        description={t("overview.description")}
        actions={
          <Button asChild variant="outline">
            <Link to="/app/onboarding">{t("overview.addSite")}</Link>
          </Button>
        }
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map(({ icon: Icon, term, label, value }) => (
          <Card key={term ?? label}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-muted-foreground text-sm font-medium">
                {term ? <Jargon term={term} /> : label}
              </CardTitle>
              <Icon className="text-muted-foreground size-4" aria-hidden />
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="mt-6">
        <CardContent className="text-muted-foreground py-6 text-sm">
          {t("overview.trackingSoon", {
            keywords: usage?.keywords ?? 0,
            prompts: usage?.prompts ?? 0,
          })}
        </CardContent>
      </Card>
    </>
  );
}
