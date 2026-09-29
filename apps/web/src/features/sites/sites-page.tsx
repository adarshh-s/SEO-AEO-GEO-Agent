import { Globe, Plus } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { EmptyState, ErrorState, PageHeader } from "@/components/ui/states";
import { useSites } from "@/lib/queries";

export function SitesPage() {
  const { t } = useTranslation("app");
  const tc = useTranslation().t;
  const sites = useSites();
  const add = (
    <Button asChild>
      <Link to="/app/onboarding">
        <Plus className="size-4" />
        {t("sites.add")}
      </Link>
    </Button>
  );
  return (
    <>
      <PageHeader title={t("sites.title")} description={t("sites.description")} actions={add} />
      {sites.isPending ? (
        <PageLoader />
      ) : sites.isError ? (
        <ErrorState error={sites.error} onRetry={() => void sites.refetch()} />
      ) : sites.data.length === 0 ? (
        <EmptyState
          icon={Globe}
          title={t("sites.emptyTitle")}
          description={t("sites.emptyBody")}
          action={add}
        />
      ) : (
        <Card className="divide-y">
          {sites.data.map((s) => (
            <Link
              key={s.id}
              to={`/app/sites/${s.id}`}
              className="hover:bg-muted/50 flex flex-wrap items-center gap-3 p-4"
            >
              <Globe className="text-muted-foreground size-5" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="font-medium">{s.name}</p>
                <p className="text-muted-foreground text-sm" dir="ltr">
                  {s.domain}
                </p>
              </div>
              <Badge variant="muted">{tc(`platforms.${s.platform}`)}</Badge>
              {[s.primary_language, ...s.additional_languages].map((l) => (
                <Badge key={l}>{tc(`languageNames.${l}`)}</Badge>
              ))}
              <Badge variant={s.verified_at ? "success" : "warning"}>
                {s.verified_at ? t("sites.verified") : t("sites.notVerified")}
              </Badge>
            </Link>
          ))}
        </Card>
      )}
    </>
  );
}
