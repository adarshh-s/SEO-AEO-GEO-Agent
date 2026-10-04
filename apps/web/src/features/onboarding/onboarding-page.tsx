import { useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input, Select, Textarea } from "@/components/ui/input";
import { Jargon } from "@/components/ui/jargon";
import { api } from "@/lib/api";
import type { AnalyzeOut, CompleteIn, Platform, SiteOut, SuggestOut } from "@/lib/api-types";
import { BRAND } from "@/lib/brand";
import { CDN_URL, CONTACT_EMAIL } from "@/lib/config";
import { errorMessage } from "@/lib/errors";
import { useOrg, useOrgKey } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { CONNECT_OPTIONS, PLATFORMS } from "./connect-options";

const STEPS = ["website", "details", "languages", "tracking", "connect", "plan"] as const;
type Step = (typeof STEPS)[number];

export type Details = {
  homepage_url: string;
  name: string;
  platform: Platform;
  industry: string;
  country: string;
  city: string;
  brand_en: string;
  brand_ar: string;
  competitors: string;
};

type Item = { text: string; language: string; selected: boolean; intent?: string };

function Stepper({ current }: { current: Step }) {
  const { t } = useTranslation("onboarding");
  const idx = STEPS.indexOf(current);
  return (
    <ol className="mb-8 flex flex-wrap gap-2" aria-label={t("progress")}>
      {STEPS.map((s, i) => (
        <li
          key={s}
          aria-current={s === current ? "step" : undefined}
          className={cn(
            "flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium",
            i < idx
              ? "bg-green-100 text-green-800"
              : i === idx
                ? "bg-primary text-primary-foreground"
                : "bg-background text-muted-foreground",
          )}
        >
          {i < idx ? <Check className="size-3" aria-hidden /> : <span>{i + 1}</span>}
          {t(`steps.${s}`)}
        </li>
      ))}
    </ol>
  );
}

/** Explains why some detected fields may be empty ("unreachable", "ai_unavailable", …). */
function AnalysisNotice({ notice }: { notice: string | null | undefined }) {
  const { t } = useTranslation("onboarding");
  if (!notice) return null;
  return (
    <Alert tone={notice === "unreachable" ? "warning" : "info"}>{t(`notices.${notice}`)}</Alert>
  );
}

export function OnboardingPage() {
  const { t } = useTranslation("onboarding");
  const navigate = useNavigate();
  const qc = useQueryClient();
  const orgId = useOrgKey();
  const [step, setStep] = useState<Step>("website");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [url, setUrl] = useState("");
  const [analysis, setAnalysis] = useState<AnalyzeOut | null>(null);
  const [details, setDetails] = useState<Details | null>(null);
  const [addArabic, setAddArabic] = useState(false); // Arabic is opt-in, never preselected
  const [keywords, setKeywords] = useState<Item[]>([]);
  const [prompts, setPrompts] = useState<Item[]>([]);
  const [suggestionSource, setSuggestionSource] = useState<string | null>(null);
  const [site, setSite] = useState<SiteOut | null>(null);

  const languages = useMemo(() => (addArabic ? ["en", "ar"] : ["en"]), [addArabic]);

  async function run(fn: () => Promise<void>) {
    setError(null);
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setError(errorMessage(e, t));
    } finally {
      setBusy(false);
    }
  }

  const analyze = () =>
    run(async () => {
      const a = await api<AnalyzeOut>("/onboarding/analyze", { method: "POST", body: { url } });
      setAnalysis(a);
      setDetails({
        homepage_url: a.homepage_url,
        name: a.brand_name,
        platform: a.platform as Platform,
        industry: a.industry ?? "",
        country: a.country,
        city: a.city ?? "",
        brand_en: a.brand_name,
        brand_ar: "",
        competitors: a.competitors.join("\n"),
      });
      setStep("details");
    });

  const loadSuggestions = () =>
    run(async () => {
      if (!details) return;
      const s = await api<SuggestOut>("/onboarding/suggestions", {
        method: "POST",
        body: {
          brand_name: details.brand_en || details.name,
          industry: details.industry,
          city: details.city || null,
          country: details.country || null,
          site_summary: analysis?.summary ?? null,
          languages,
        },
      });
      setSuggestionSource(s.source);
      setKeywords(
        s.keywords.map((k) => ({ text: k.keyword, language: k.language, selected: true })),
      );
      setPrompts(
        s.prompts.map((p) => ({
          text: p.prompt_text,
          language: p.language,
          intent: p.intent,
          selected: true,
        })),
      );
      setStep("tracking");
    });

  const complete = () =>
    run(async () => {
      if (!details) return;
      const brand_names: Record<string, string[]> = { en: [details.brand_en || details.name] };
      if (addArabic && details.brand_ar.trim()) brand_names.ar = [details.brand_ar.trim()];
      const body: CompleteIn = {
        site: {
          homepage_url: details.homepage_url,
          name: details.name,
          platform: details.platform,
          platform_confirmed: true,
          primary_language: "en",
          additional_languages: addArabic ? ["ar"] : [],
          default_country: details.country,
          default_city: details.city || null,
          industry: details.industry || null,
          brand_names,
          competitor_domains: details.competitors.split(/[\s,]+/).filter(Boolean),
        },
        keywords: keywords
          .filter((k) => k.selected)
          .map((k) => ({ keyword: k.text, language: k.language, device: "desktop", tags: [] })),
        prompts: prompts
          .filter((p) => p.selected)
          .map((p) => ({
            prompt_text: p.text,
            language: p.language,
            tags: [],
            intent: (p.intent ?? "informational") as NonNullable<
              CompleteIn["prompts"]
            >[number]["intent"],
          })),
      };
      const created = await api<SiteOut>("/onboarding/complete", { method: "POST", body });
      setSite(created);
      qc.setQueryData<SiteOut[]>(["sites", orgId], (old) => [...(old ?? []), created]);
      void qc.invalidateQueries({ queryKey: ["sites"] });
      void qc.invalidateQueries({ queryKey: ["org"] });
      setStep("connect");
    });

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-2 text-2xl font-semibold">{t("title")}</h1>
      <p className="text-muted-foreground mb-6 text-sm">{t("subtitle")}</p>
      <Stepper current={step} />
      {error && (
        <Alert tone="error" className="mb-4">
          {error}
        </Alert>
      )}

      {step === "website" && (
        <Card>
          <CardHeader>
            <CardTitle>{t("website.title")}</CardTitle>
            <CardDescription>{t("website.description")}</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="flex flex-col gap-3 sm:flex-row"
              onSubmit={(e) => {
                e.preventDefault();
                void analyze();
              }}
            >
              <Input
                aria-label={t("website.label")}
                placeholder="example.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                dir="ltr"
                autoFocus
              />
              <Button type="submit" loading={busy} disabled={!url.trim()}>
                {t("website.analyze")}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {step === "details" && details && analysis && (
        <DetailsStep
          details={details}
          onChange={setDetails}
          analysis={analysis}
          onBack={() => setStep("website")}
          onNext={() => setStep("languages")}
        />
      )}

      {step === "languages" && details && analysis && (
        <Card>
          <CardHeader>
            <CardTitle>{t("languages.title")}</CardTitle>
            <CardDescription>{t("languages.description")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex items-center gap-3 rounded-md border p-3">
              <input type="checkbox" checked disabled className="size-4" />
              <span className="font-medium">{t("languages.english")}</span>
              <Badge variant="muted" className="ms-auto">
                {t("languages.primary")}
              </Badge>
            </label>
            <label className="flex items-center gap-3 rounded-md border p-3">
              <input
                type="checkbox"
                className="size-4"
                checked={addArabic}
                onChange={(e) => setAddArabic(e.target.checked)}
              />
              <span className="font-medium">{t("languages.addArabic")}</span>
              <span className="text-muted-foreground ms-auto text-xs">
                {t("languages.optional")}
              </span>
            </label>
            {analysis.detected_languages.includes("ar") && !addArabic && (
              <Alert tone="info">{t("languages.arabicDetected")}</Alert>
            )}
            {addArabic && (
              <>
                <Field label={t("languages.arabicBrand")} hint={t("languages.arabicBrandHint")}>
                  <Input
                    dir="rtl"
                    lang="ar"
                    value={details.brand_ar}
                    onChange={(e) => setDetails({ ...details, brand_ar: e.target.value })}
                  />
                </Field>
                <p className="text-muted-foreground text-xs">{t("languages.planNote")}</p>
              </>
            )}
            <StepNav
              onBack={() => setStep("details")}
              onNext={() => void loadSuggestions()}
              busy={busy}
            />
          </CardContent>
        </Card>
      )}

      {step === "tracking" && (
        <div className="space-y-4">
          {suggestionSource === "template" && <Alert tone="info">{t("notices.template")}</Alert>}
          <ItemList
            title={t("tracking.keywordsTitle")}
            description={t("tracking.keywordsDescription")}
            jargon="keyword"
            items={keywords}
            onChange={setKeywords}
            languages={languages}
            addLabel={t("tracking.addKeyword")}
          />
          <ItemList
            title={t("tracking.promptsTitle")}
            description={t("tracking.promptsDescription")}
            jargon="aiPrompt"
            items={prompts}
            onChange={setPrompts}
            languages={languages}
            addLabel={t("tracking.addPrompt")}
            multiline
          />
          <StepNav
            onBack={() => setStep("languages")}
            onNext={() => void complete()}
            busy={busy}
            nextLabel={t("tracking.create")}
          />
        </div>
      )}

      {step === "connect" && site && <ConnectStep site={site} onNext={() => setStep("plan")} />}

      {step === "plan" && <PlanStep onFinish={() => navigate("/app", { replace: true })} />}
    </div>
  );
}

function StepNav({
  onBack,
  onNext,
  busy,
  nextLabel,
  nextDisabled,
}: {
  onBack?: () => void;
  onNext: () => void;
  busy?: boolean;
  nextLabel?: string;
  nextDisabled?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex justify-between gap-3 pt-2">
      {onBack ? (
        <Button variant="outline" onClick={onBack}>
          {t("back")}
        </Button>
      ) : (
        <span />
      )}
      <Button onClick={onNext} loading={busy} disabled={nextDisabled}>
        {nextLabel ?? t("next")}
      </Button>
    </div>
  );
}

export function DetailsStep({
  details,
  onChange,
  analysis,
  onBack,
  onNext,
}: {
  details: Details;
  onChange: (d: Details) => void;
  analysis: AnalyzeOut;
  onBack: () => void;
  onNext: () => void;
}) {
  const { t } = useTranslation("onboarding");
  const tc = useTranslation().t;
  const set =
    (k: keyof Details) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      onChange({ ...details, [k]: e.target.value });
  const missing =
    !details.name.trim() || !details.industry.trim() || !/^[A-Za-z]{2}$/.test(details.country);
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("details.title")}</CardTitle>
        <CardDescription>{t("details.description", { domain: analysis.domain })}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <AnalysisNotice notice={analysis.notice} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("details.name")}>
            <Input value={details.name} onChange={set("name")} />
          </Field>
          <Field label={t("details.platform")} hint={t("details.platformHint")}>
            <Select value={details.platform} onChange={set("platform")}>
              {PLATFORMS.map((p) => (
                <option key={p} value={p}>
                  {tc(`platforms.${p}`)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t("details.brand")} hint={t("details.brandHint")}>
            <Input value={details.brand_en} onChange={set("brand_en")} />
          </Field>
          <Field label={t("details.industry")} hint={t("details.industryHint")}>
            <Input
              value={details.industry}
              onChange={set("industry")}
              placeholder={t("details.industryPlaceholder")}
            />
          </Field>
          <Field label={t("details.country")} hint={t("details.countryHint")}>
            <Input value={details.country} maxLength={2} onChange={set("country")} dir="ltr" />
          </Field>
          <Field label={t("details.city")}>
            <Input value={details.city} onChange={set("city")} />
          </Field>
        </div>
        <Field
          label={<Jargon term="competitor">{t("details.competitors")}</Jargon>}
          hint={t("details.competitorsHint")}
        >
          <Textarea
            value={details.competitors}
            onChange={set("competitors")}
            dir="ltr"
            placeholder="competitor.com"
          />
        </Field>
        <StepNav onBack={onBack} onNext={onNext} nextDisabled={missing} />
      </CardContent>
    </Card>
  );
}

function ItemList({
  title,
  description,
  jargon,
  items,
  onChange,
  languages,
  addLabel,
  multiline,
}: {
  title: string;
  description: string;
  jargon: string;
  items: Item[];
  onChange: (i: Item[]) => void;
  languages: string[];
  addLabel: string;
  multiline?: boolean;
}) {
  const { t } = useTranslation("onboarding");
  const tc = useTranslation().t;
  const [draft, setDraft] = useState("");
  const [draftLang, setDraftLang] = useState(languages[0] ?? "en");
  const toggle = (i: number) =>
    onChange(items.map((it, j) => (j === i ? { ...it, selected: !it.selected } : it)));
  const remove = (i: number) => onChange(items.filter((_, j) => j !== i));
  const add = () => {
    if (!draft.trim()) return;
    onChange([...items, { text: draft.trim(), language: draftLang, selected: true }]);
    setDraft("");
  };
  const selected = items.filter((i) => i.selected).length;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Jargon term={jargon}>{title}</Jargon>
        </CardTitle>
        <CardDescription>
          {description} {t("tracking.selected", { count: selected })}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <ul className="divide-y rounded-md border">
          {items.map((it, i) => (
            <li
              key={`${it.language}-${it.text}-${i}`}
              className="flex items-center gap-3 px-3 py-2"
            >
              <input
                type="checkbox"
                className="size-4"
                checked={it.selected}
                onChange={() => toggle(i)}
                aria-label={it.text}
              />
              <span className="flex-1 text-sm" dir="auto" lang={it.language}>
                {it.text}
              </span>
              {languages.length > 1 && (
                <Badge variant="muted">{tc(`languageNames.${it.language}`)}</Badge>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => remove(i)}
                aria-label={tc("remove")}
              >
                <Trash2 className="size-4" />
              </Button>
            </li>
          ))}
          {items.length === 0 && (
            <li className="text-muted-foreground px-3 py-6 text-center text-sm">
              {t("tracking.empty")}
            </li>
          )}
        </ul>
        <div className="flex flex-col gap-2 sm:flex-row">
          {multiline ? (
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={addLabel}
              dir="auto"
              className="min-h-10"
            />
          ) : (
            <Input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={addLabel}
              dir="auto"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  add();
                }
              }}
            />
          )}
          {languages.length > 1 && (
            <Select
              value={draftLang}
              onChange={(e) => setDraftLang(e.target.value)}
              className="sm:w-36"
              aria-label={tc("language.label")}
            >
              {languages.map((l) => (
                <option key={l} value={l}>
                  {tc(`languageNames.${l}`)}
                </option>
              ))}
            </Select>
          )}
          <Button variant="outline" onClick={add} disabled={!draft.trim()}>
            <Plus className="size-4" />
            {tc("add")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function CopyBlock({ code }: { code: string }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  return (
    <div className="relative">
      <pre
        dir="ltr"
        className="bg-foreground text-background overflow-x-auto rounded-md p-3 pe-12 text-xs"
      >
        <code>{code}</code>
      </pre>
      <Button
        size="icon"
        variant="ghost"
        className="text-background absolute end-1 top-1 hover:bg-white/10"
        aria-label={t("copy")}
        onClick={() => {
          void navigator.clipboard?.writeText(code);
          setCopied(true);
        }}
      >
        {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
      </Button>
    </div>
  );
}

function ConnectStep({ site, onNext }: { site: SiteOut; onNext: () => void }) {
  const { t } = useTranslation("onboarding");
  const tc = useTranslation().t;
  const options = CONNECT_OPTIONS[site.platform as Platform] ?? CONNECT_OPTIONS.unknown;
  const snippet = `<script async src="${CDN_URL}/${BRAND.snippet_filename}" data-site="${site.site_key}"></script>`;
  const meta = `<meta name="${BRAND.verification_meta_name}" content="${site.verification_token}">`;
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>{t("connect.title")}</CardTitle>
          <CardDescription>
            {t("connect.description", { platform: tc(`platforms.${site.platform}`) })}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {options.map((o, i) => (
            <div key={o.method} className="rounded-md border p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{t(`connect.methods.${o.method}.title`)}</span>
                <Badge variant={o.kind === "automatic" ? "success" : "muted"}>
                  {t(`connect.kinds.${o.kind}`)}
                  {i === 0 ? ` · ${t("connect.recommended")}` : ""}
                </Badge>
                {!o.serverSide && <Badge variant="warning">{t("connect.clientSide")}</Badge>}
              </div>
              <p className="text-muted-foreground mt-1 text-sm">
                {t(`connect.methods.${o.method}.body`)}
              </p>
              {o.method === "snippet" && (
                <div className="mt-3">
                  <CopyBlock code={snippet} />
                </div>
              )}
            </div>
          ))}
          <Alert tone="warning">{t("connect.snippetLimitation")}</Alert>
          <Alert tone="info">{t("connect.comingSoon")}</Alert>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>
            <Jargon term="verification">{t("connect.verifyTitle")}</Jargon>
          </CardTitle>
          <CardDescription>{t("connect.verifyDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <CopyBlock code={meta} />
        </CardContent>
      </Card>
      <StepNav onNext={onNext} nextLabel={t("connect.later")} />
    </div>
  );
}

function PlanStep({ onFinish }: { onFinish: () => void }) {
  const { t } = useTranslation("onboarding");
  const org = useOrg();
  const plan = org.data?.plan;
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("plan.title")}</CardTitle>
        <CardDescription>{t("plan.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {plan && (
          <div className="rounded-md border p-4">
            <div className="flex items-center gap-2">
              <span className="font-semibold">{plan.name}</span>
              {plan.trial_days ? (
                <Badge>{t("plan.trialDays", { count: plan.trial_days })}</Badge>
              ) : null}
            </div>
            <p className="text-muted-foreground mt-1 text-sm">
              {t("plan.limits", {
                sites: plan.max_sites,
                keywords: plan.max_keywords,
                prompts: plan.max_prompts,
              })}
            </p>
          </div>
        )}
        <p className="text-sm">
          {t("plan.upgrade")}{" "}
          <a className="text-primary hover:underline" href={`mailto:${CONTACT_EMAIL}`}>
            {CONTACT_EMAIL}
          </a>
          {" · "}
          <Link className="text-primary hover:underline" to="/pricing">
            {t("plan.seePlans")}
          </Link>
        </p>
        <div className="flex justify-end">
          <Button onClick={onFinish}>{t("plan.finish")}</Button>
        </div>
      </CardContent>
    </Card>
  );
}
