import {
  ArrowRight,
  Bot,
  Check,
  ChevronDown,
  LineChart,
  Mail,
  Sparkles,
  Wrench,
} from "lucide-react";
import { useState } from "react";
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
import { PRODUCT_NAME } from "@/lib/brand";
import { CONNECT_OPTIONS, PLATFORMS } from "@/features/onboarding/connect-options";

export function LandingPage() {
  const { t } = useTranslation("public");
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const features = [
    { icon: LineChart, key: "track" },
    { icon: Bot, key: "ai" },
    { icon: Wrench, key: "fix" },
  ];

  const faqItems = (t("faq.items", { returnObjects: true }) as { q: string; a: string }[]) || [];

  return (
    <div className="space-y-24 py-12">
      {/* 1. Hero Section */}
      <section className="mx-auto max-w-5xl px-4 text-center">
        <div className="border-primary/20 bg-primary/5 text-primary mb-6 inline-flex items-center gap-2 rounded-full border px-3.5 py-1 text-xs font-semibold">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Next-Gen SEO & AI Engine Optimization (AEO)</span>
        </div>

        <h1 className="text-foreground mx-auto max-w-4xl text-4xl leading-tight font-extrabold tracking-tight sm:text-6xl">
          {t("hero.title")}
        </h1>

        <p className="text-muted-foreground mx-auto mt-6 max-w-2xl text-lg leading-relaxed sm:text-xl">
          {t("hero.subtitle")}
        </p>

        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <Button asChild size="lg" className="h-12 px-6 text-base font-semibold">
            <Link to="/signup">
              {t("hero.cta")}
              <ArrowRight className="ms-2 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline" className="h-12 px-6 text-base font-semibold">
            <Link to="/pricing">{t("nav.pricing")}</Link>
          </Button>
        </div>

        <p className="text-muted-foreground mt-4 text-xs">{t("hero.disclaimer")}</p>

        {/* Platform support ticker / badges */}
        <div className="border-border/60 mt-14 border-t border-b py-6">
          <p className="text-muted-foreground mb-4 text-xs font-semibold tracking-wider uppercase">
            Unified Optimization For Every Platform
          </p>
          <div className="text-muted-foreground/80 flex flex-wrap items-center justify-center gap-6 text-sm font-medium sm:gap-10">
            <span>WordPress</span>
            <span>Shopify</span>
            <span>Next.js / React</span>
            <span>Cloudflare Edge</span>
            <span>Salla (سلة)</span>
            <span>Zid (زد)</span>
            <span>Webflow</span>
            <span>Wix</span>
          </div>
        </div>
      </section>

      {/* 2. Core Pillars / Features Grid */}
      <section className="mx-auto max-w-6xl px-4">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <h2 className="text-2xl font-bold sm:text-3xl">Comprehensive Search Intelligence</h2>
          <p className="text-muted-foreground mt-2 text-sm sm:text-base">
            From classic Google rankings to modern LLM referral tracking, {PRODUCT_NAME} bridges
            traditional SEO and generative AI answer visibility.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {features.map(({ icon: Icon, key }) => (
            <Card
              key={key}
              className="border-border/80 hover:border-primary/40 flex flex-col transition-colors"
            >
              <CardHeader>
                <div className="bg-primary/10 mb-2 w-fit rounded-lg p-2.5">
                  <Icon className="text-primary size-5" aria-hidden />
                </div>
                <CardTitle className="text-lg">{t(`features.${key}.title`)}</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground flex-1 text-sm leading-relaxed">
                {t(`features.${key}.body`)}
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* 3. How It Works Section */}
      <section className="bg-muted/30 border-border border-y py-16">
        <div className="mx-auto max-w-6xl px-4">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-2xl font-bold sm:text-3xl">How {PRODUCT_NAME} Works</h2>
            <p className="text-muted-foreground mt-2 text-sm sm:text-base">
              Automated, safe, and transparent workflow designed for modern web engineering and
              marketing teams.
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-3">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-full text-sm font-bold">
                  1
                </span>
                <h3 className="text-base font-semibold">Connect Your Site</h3>
              </div>
              <p className="text-muted-foreground ps-11 text-sm leading-relaxed">
                Install our lightweight cookieless snippet, deploy via WordPress/Shopify apps, or
                bind our Cloudflare edge worker in minutes.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-full text-sm font-bold">
                  2
                </span>
                <h3 className="text-base font-semibold">Detect & Diagnose Gaps</h3>
              </div>
              <p className="text-muted-foreground ps-11 text-sm leading-relaxed">
                {PRODUCT_NAME} crawls your pages and benchmarks them against top ranking competitors
                and AI citation patterns to uncover missing schema and content signals.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-full text-sm font-bold">
                  3
                </span>
                <h3 className="text-base font-semibold">Approve & Deploy Fixes</h3>
              </div>
              <p className="text-muted-foreground ps-11 text-sm leading-relaxed">
                Review generated structured data and title/meta fixes in your inbox. Approve changes
                with one click, or roll back at any time.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Frequently Asked Questions */}
      {Array.isArray(faqItems) && faqItems.length > 0 && (
        <section className="mx-auto max-w-3xl px-4">
          <div className="mb-10 text-center">
            <h2 className="text-2xl font-bold sm:text-3xl">{t("faq.title")}</h2>
            <p className="text-muted-foreground mt-2 text-sm">{t("faq.subtitle")}</p>
          </div>

          <div className="divide-border bg-card divide-y overflow-hidden rounded-xl border">
            {faqItems.map((item, idx) => (
              <div key={idx} className="transition-colors">
                <button
                  type="button"
                  className="hover:bg-muted/20 flex w-full items-center justify-between p-4 text-start text-sm font-medium"
                  onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                >
                  <span>{item.q}</span>
                  <ChevronDown
                    className={`text-muted-foreground h-4 w-4 shrink-0 transition-transform duration-200 ${
                      openFaq === idx ? "rotate-180" : ""
                    }`}
                  />
                </button>
                {openFaq === idx && (
                  <div className="text-muted-foreground border-border/40 bg-muted/5 border-t px-4 pt-1 pb-4 text-xs leading-relaxed sm:text-sm">
                    {item.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 5. Bottom Call to Action */}
      <section className="mx-auto max-w-5xl px-4 text-center">
        <Card className="border-primary/20 bg-primary/5 p-8 sm:p-12">
          <h2 className="text-foreground text-2xl font-bold sm:text-3xl">
            Ready to expand your organic & AI search presence?
          </h2>
          <p className="text-muted-foreground mx-auto mt-3 max-w-xl text-sm sm:text-base">
            Start tracking rankings, measuring AI citations, and deploying technical optimizations
            today.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <Button asChild size="lg" className="h-11 px-8 font-semibold">
              <Link to="/signup">{t("hero.cta")}</Link>
            </Button>
          </div>
        </Card>
      </section>
    </div>
  );
}

export function PricingPage() {
  const { t } = useTranslation("public");
  const plans = usePublicPlans();

  return (
    <div className="mx-auto max-w-6xl space-y-12 px-4 py-16">
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="text-3xl font-extrabold sm:text-4xl">{t("pricing.title")}</h1>
        <p className="text-muted-foreground mt-3 text-base">{t("pricing.subtitle")}</p>
      </div>

      <div>
        {plans.isPending ? (
          <PageLoader />
        ) : plans.isError ? (
          <ErrorState error={plans.error} onRetry={() => void plans.refetch()} />
        ) : (
          <div className="grid gap-6 md:grid-cols-3">
            {plans.data.map((p) => {
              const isPopular = p.code === "growth";
              return (
                <Card
                  key={p.code}
                  className={`relative flex flex-col transition-all ${
                    isPopular ? "border-primary shadow-md md:-translate-y-1" : "border-border"
                  }`}
                >
                  {isPopular && (
                    <div className="absolute start-1/2 -top-3 -translate-x-1/2">
                      <Badge
                        variant="default"
                        className="text-[11px] font-bold tracking-wider uppercase"
                      >
                        Most Popular
                      </Badge>
                    </div>
                  )}

                  <CardHeader className="pt-6">
                    <CardTitle className="text-xl font-bold">{p.name}</CardTitle>
                    <p className="text-muted-foreground mt-1 text-xs">
                      {p.code === "starter"
                        ? "Essential tracking for growing individual websites."
                        : p.code === "growth"
                          ? "Comprehensive search & AI intelligence for scaling brands."
                          : "High-volume tracking and enterprise multi-domain coverage."}
                    </p>
                  </CardHeader>

                  <CardContent className="flex flex-1 flex-col justify-between gap-6">
                    <ul className="space-y-2.5 text-xs sm:text-sm">
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
                        <li key={line} className="flex items-start gap-2">
                          <Check className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden />
                          <span className="text-foreground">{line}</span>
                        </li>
                      ))}
                    </ul>

                    <Button
                      asChild
                      variant={isPopular ? "default" : "outline"}
                      className="w-full font-medium"
                    >
                      <a
                        href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(
                          `Inquiry regarding ${p.name} Plan`,
                        )}&body=${encodeURIComponent(
                          `Hello ${PRODUCT_NAME} Team,\n\nI would like to get started with the ${p.name} plan for my website.\n\nMy website: \nCompany name: `,
                        )}`}
                      >
                        <Mail className="me-2 h-4 w-4" />
                        {t("pricing.contact")}
                      </a>
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      <div className="bg-muted/20 mx-auto max-w-2xl space-y-2 rounded-lg border p-6 text-center">
        <h4 className="text-sm font-semibold">14-Day Full-Featured Trial</h4>
        <p className="text-muted-foreground text-xs leading-relaxed">
          {t("pricing.trial")} Experience Google rank tracking, LLM citation checks, gap diagnosis,
          and executive PDF reports with zero upfront commitment.
        </p>
        <div className="pt-2">
          <Button asChild size="sm">
            <Link to="/signup">Start Free Trial Now</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}

export function IntegrationsPage() {
  const { t } = useTranslation("public");
  const tc = useTranslation().t;
  const [filterCategory, setFilterCategory] = useState<string>("all");

  const categories = [
    { id: "all", label: "All Integrations" },
    { id: "ecommerce", label: "E-Commerce" },
    { id: "modern", label: "Headless & Modern Web" },
    { id: "cms", label: "CMS & Site Builders" },
  ];

  const getPlatformCategory = (p: string) => {
    if (["shopify", "salla", "zid", "woocommerce"].includes(p)) return "ecommerce";
    if (["nextjs", "cloudflare", "github"].includes(p)) return "modern";
    return "cms";
  };

  const platforms = PLATFORMS.filter((p) => p !== "unknown");
  const filteredPlatforms = platforms.filter((p) => {
    if (filterCategory === "all") return true;
    return getPlatformCategory(p) === filterCategory;
  });

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-4 py-16">
      <div className="max-w-2xl">
        <h1 className="text-3xl font-extrabold sm:text-4xl">{t("integrations.title")}</h1>
        <p className="text-muted-foreground mt-3 text-base">{t("integrations.subtitle")}</p>
      </div>

      {/* Filter Chips */}
      <div className="flex flex-wrap gap-2 border-b pb-4">
        {categories.map((c) => (
          <Button
            key={c.id}
            variant={filterCategory === c.id ? "default" : "outline"}
            size="sm"
            className="h-8 text-xs"
            onClick={() => setFilterCategory(c.id)}
          >
            {c.label}
          </Button>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filteredPlatforms.map((p) => {
          const best = CONNECT_OPTIONS[p][0]!;
          return (
            <Card
              key={p}
              className="hover:border-primary/40 flex flex-col justify-between transition-colors"
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <CardTitle className="text-base font-semibold">{tc(`platforms.${p}`)}</CardTitle>
                <Badge variant={best.kind === "automatic" ? "success" : "muted"}>
                  {t(`integrations.kinds.${best.kind}`)}
                </Badge>
              </CardHeader>
              <CardContent className="text-muted-foreground text-xs leading-relaxed">
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
      <p className="text-muted-foreground mt-2 text-xs">{t("legalDraft")}</p>
      {Array.isArray(sections) &&
        sections.map((s) => (
          <section key={s.h} className="mt-8">
            <h2 className="text-lg font-semibold">{s.h}</h2>
            <p className="text-muted-foreground mt-2 text-sm leading-relaxed">{s.p}</p>
          </section>
        ))}
    </article>
  );
}
