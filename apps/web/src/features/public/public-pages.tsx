import { Bot, Check, LineChart, Wrench } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { ErrorState } from "@/components/ui/states";
import { CONTACT_EMAIL } from "@/lib/config";
import { formatNumber } from "@/lib/i18n";
import { usePublicPlans } from "@/lib/queries";
import { CONNECT_OPTIONS, PLATFORMS } from "@/features/onboarding/connect-options";

export function LandingPage() {
  const { t } = useTranslation("public");
  const features = [
    { icon: LineChart, key: "track" },
    { icon: Bot, key: "ai" },
    { icon: Wrench, key: "fix" },
  ];
  return (
    <div className="mx-auto max-w-6xl px-4 py-16">
      <section className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">{t("hero.title")}</h1>
        <p className="text-muted-foreground mt-4 text-lg">{t("hero.subtitle")}</p>
        <div className="mt-8 flex justify-center gap-3">
          <Button asChild size="lg">
            <Link to="/signup">{t("hero.cta")}</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link to="/pricing">{t("nav.pricing")}</Link>
          </Button>
        </div>
        <p className="text-muted-foreground mt-4 text-xs">{t("hero.disclaimer")}</p>
      </section>
      <section className="mt-16 grid gap-6 md:grid-cols-3">
        {features.map(({ icon: Icon, key }) => (
          <Card key={key}>
            <CardHeader>
              <Icon className="text-primary size-6" aria-hidden />
              <CardTitle>{t(`features.${key}.title`)}</CardTitle>
            </CardHeader>
            <CardContent className="text-muted-foreground text-sm">
              {t(`features.${key}.body`)}
            </CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}

export function PricingPage() {
  const { t } = useTranslation("public");
  const plans = usePublicPlans();
  return (
    <div className="mx-auto max-w-6xl px-4 py-16">
      <h1 className="text-center text-3xl font-bold">{t("pricing.title")}</h1>
      <p className="text-muted-foreground mx-auto mt-3 max-w-2xl text-center">
        {t("pricing.subtitle")}
      </p>
      <div className="mt-10">
        {plans.isPending ? (
          <PageLoader />
        ) : plans.isError ? (
          <ErrorState error={plans.error} onRetry={() => void plans.refetch()} />
        ) : (
          <div className="grid gap-6 md:grid-cols-3">
            {plans.data.map((p) => (
              <Card key={p.code} className="flex flex-col">
                <CardHeader>
                  <CardTitle>{p.name}</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col gap-4">
                  <ul className="flex-1 space-y-2 text-sm">
                    {[
                      t("pricing.sites", { count: p.max_sites, n: formatNumber(p.max_sites) }),
                      t("pricing.keywords", { n: formatNumber(p.max_keywords) }),
                      t("pricing.prompts", { n: formatNumber(p.max_prompts) }),
                      t("pricing.engines", { count: p.max_engines, n: p.max_engines }),
                      t(`pricing.frequency.${p.check_frequency}`),
                      t("pricing.audits", { n: formatNumber(p.audits_per_month) }),
                      p.addon_languages.includes("ar")
                        ? t("pricing.arabicAddon")
                        : t("pricing.languages", {
                            count: p.max_languages_per_site,
                            n: p.max_languages_per_site,
                          }),
                    ].map((line) => (
                      <li key={line} className="flex gap-2">
                        <Check className="text-success mt-0.5 size-4 shrink-0" aria-hidden />
                        {line}
                      </li>
                    ))}
                  </ul>
                  <Button asChild variant="outline">
                    <a href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(p.name)}`}>
                      {t("pricing.contact")}
                    </a>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
      <p className="text-muted-foreground mt-8 text-center text-sm">{t("pricing.trial")}</p>
    </div>
  );
}

export function IntegrationsPage() {
  const { t } = useTranslation("public");
  const tc = useTranslation().t;
  return (
    <div className="mx-auto max-w-6xl px-4 py-16">
      <h1 className="text-3xl font-bold">{t("integrations.title")}</h1>
      <p className="text-muted-foreground mt-3 max-w-2xl">{t("integrations.subtitle")}</p>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {PLATFORMS.filter((p) => p !== "unknown").map((p) => {
          const best = CONNECT_OPTIONS[p][0]!;
          return (
            <Card key={p}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-base">{tc(`platforms.${p}`)}</CardTitle>
                <Badge variant={best.kind === "automatic" ? "success" : "muted"}>
                  {t(`integrations.kinds.${best.kind}`)}
                </Badge>
              </CardHeader>
              <CardContent className="text-muted-foreground text-sm">
                {t(`integrations.methods.${best.method}`)}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export function LegalPage({ doc }: { doc: "privacy" | "terms" }) {
  const { t } = useTranslation("public");
  const sections = t(`${doc}.sections`, { returnObjects: true }) as { h: string; p: string }[];
  return (
    <article className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-3xl font-bold">{t(`${doc}.title`)}</h1>
      <p className="text-muted-foreground mt-2 text-sm">{t("legalDraft")}</p>
      {Array.isArray(sections) &&
        sections.map((s) => (
          <section key={s.h} className="mt-8">
            <h2 className="text-lg font-semibold">{s.h}</h2>
            <p className="text-muted-foreground mt-2">{s.p}</p>
          </section>
        ))}
    </article>
  );
}
