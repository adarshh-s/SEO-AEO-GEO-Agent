import {
  ArrowDown,
  ArrowUp,
  BarChart3,
  ExternalLink,
  Minus,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { EmptyState, ErrorState, PageHeader } from "@/components/ui/states";
import type { RankedKeywordOut } from "@/lib/api-types";
import { formatNumber } from "@/lib/i18n";
import {
  useRankings,
  useSites,
  useTriggerAllKeywordChecks,
  useTriggerKeywordCheck,
} from "@/lib/queries";

export function KeywordsPage() {
  const { t } = useTranslation("app");
  const tc = useTranslation().t;
  const sites = useSites();

  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [selectedLang, setSelectedLang] = useState<string>("all");

  const siteId = selectedSiteId ?? sites.data?.[0]?.id;
  const currentSite = sites.data?.find((s) => s.id === siteId);

  const rankings = useRankings(siteId);
  const triggerCheck = useTriggerKeywordCheck(siteId ?? "");
  const triggerAll = useTriggerAllKeywordChecks(siteId ?? "");

  if (sites.isPending) return <PageLoader />;
  if (sites.isError) return <ErrorState error={sites.error} onRetry={() => void sites.refetch()} />;

  if (!sites.data || sites.data.length === 0) {
    return (
      <EmptyState
        icon={BarChart3}
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

  const items = rankings.data ?? [];
  const filtered =
    selectedLang === "all" ? items : items.filter((k) => k.language === selectedLang);

  const siteLanguages = currentSite
    ? [currentSite.primary_language, ...currentSite.additional_languages]
    : [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("keywords.title")}
        description={t("keywords.description")}
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
              {triggerAll.isPending ? t("keywords.checking") : t("keywords.checkAll")}
            </Button>
          </div>
        }
      />

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

      {rankings.isPending ? (
        <PageLoader />
      ) : rankings.isError ? (
        <ErrorState error={rankings.error} onRetry={() => void rankings.refetch()} />
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="text-muted-foreground py-12 text-center text-sm">
            {t("sections.keywords.empty")}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-start text-sm">
              <thead className="bg-muted/50 border-b text-xs font-medium uppercase">
                <tr>
                  <th className="px-4 py-3 text-start">{t("keywords.keyword")}</th>
                  <th className="px-4 py-3 text-center">{t("keywords.position")}</th>
                  <th className="px-4 py-3 text-center">{t("keywords.change")}</th>
                  <th className="px-4 py-3 text-center">{t("keywords.aiOverview")}</th>
                  <th className="px-4 py-3 text-start">{t("keywords.url")}</th>
                  <th className="px-4 py-3 text-end"></th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filtered.map((k) => (
                  <KeywordRow
                    key={k.id}
                    item={k}
                    onCheck={() => triggerCheck.mutate(k.id)}
                    isChecking={triggerCheck.isPending}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

function KeywordRow({
  item,
  onCheck,
  isChecking,
}: {
  item: RankedKeywordOut;
  onCheck: () => void;
  isChecking: boolean;
}) {
  const { t } = useTranslation("app");
  const tc = useTranslation().t;

  const positionBadge = () => {
    if (item.position === null || item.position === undefined) {
      return <Badge variant="muted">{t("keywords.notRanked")}</Badge>;
    }
    if (item.position <= 3) {
      return (
        <Badge variant="default" className="bg-emerald-600 font-semibold text-white">
          #{formatNumber(item.position)}
        </Badge>
      );
    }
    if (item.position <= 10) {
      return (
        <Badge variant="default" className="bg-blue-600 text-white">
          #{formatNumber(item.position)}
        </Badge>
      );
    }
    return <Badge variant="outline">#{formatNumber(item.position)}</Badge>;
  };

  const changeDisplay = () => {
    if (
      item.position_change === null ||
      item.position_change === undefined ||
      item.position_change === 0
    ) {
      return <Minus className="text-muted-foreground inline size-4" aria-hidden />;
    }
    if (item.position_change > 0) {
      return (
        <span className="flex items-center justify-center font-medium text-emerald-600">
          <ArrowUp className="me-1 size-3.5" aria-hidden />+{formatNumber(item.position_change)}
        </span>
      );
    }
    return (
      <span className="flex items-center justify-center font-medium text-rose-600">
        <ArrowDown className="me-1 size-3.5" aria-hidden />
        {formatNumber(item.position_change)}
      </span>
    );
  };

  return (
    <tr className="hover:bg-muted/30 transition-colors">
      <td className="px-4 py-3">
        <div className="text-foreground font-medium">{item.keyword}</div>
        <div className="text-muted-foreground flex items-center gap-1.5 text-xs">
          <span>{tc(`languageNames.${item.language}`)}</span>
          <span>·</span>
          <span>{item.country}</span>
          <span>·</span>
          <span>{item.device}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-center">{positionBadge()}</td>
      <td className="px-4 py-3 text-center">{changeDisplay()}</td>
      <td className="px-4 py-3 text-center">
        {item.ai_overview_present ? (
          <div className="flex flex-col items-center gap-1">
            <Badge
              variant="outline"
              className="border-purple-300 bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300"
            >
              <Sparkles className="me-1 size-3" aria-hidden />
              AI Overview
            </Badge>
            {item.ai_overview_cites_site && (
              <span className="text-[10px] font-medium text-emerald-600">
                {t("keywords.citesSite")}
              </span>
            )}
          </div>
        ) : (
          <span className="text-muted-foreground text-xs">—</span>
        )}
      </td>
      <td className="max-w-[200px] truncate px-4 py-3 text-start">
        {item.url_ranked ? (
          <a
            href={item.url_ranked}
            target="_blank"
            rel="noreferrer"
            className="text-primary inline-flex items-center gap-1 text-xs hover:underline"
          >
            <span className="truncate" dir="ltr">
              {item.url_ranked}
            </span>
            <ExternalLink className="size-3 shrink-0" aria-hidden />
          </a>
        ) : (
          <span className="text-muted-foreground text-xs">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-end">
        <Button
          size="sm"
          variant="ghost"
          aria-label={t("keywords.checkNow")}
          disabled={isChecking}
          onClick={onCheck}
        >
          <RefreshCw className={`size-3.5 ${isChecking ? "animate-spin" : ""}`} aria-hidden />
        </Button>
      </td>
    </tr>
  );
}
