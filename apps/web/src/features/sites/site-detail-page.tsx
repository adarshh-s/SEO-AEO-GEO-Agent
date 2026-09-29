import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Pause, Play, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input, Select, Textarea } from "@/components/ui/input";
import { Jargon } from "@/components/ui/jargon";
import { PageLoader } from "@/components/ui/spinner";
import { ErrorState, PageHeader } from "@/components/ui/states";
import { api } from "@/lib/api";
import type { SiteOut } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { useKeywords, usePrompts, useSite, useUpdateSite } from "@/lib/queries";
import { useCurrentRole } from "@/stores/session";

export function SiteDetailPage() {
  const { siteId } = useParams();
  const site = useSite(siteId);
  if (site.isPending) return <PageLoader />;
  if (site.isError) return <ErrorState error={site.error} onRetry={() => void site.refetch()} />;
  return (
    <>
      <PageHeader title={site.data.name} description={site.data.domain} />
      <div className="space-y-6">
        <SiteSettingsCard site={site.data} />
        <TrackedList
          siteId={site.data.id}
          kind="keywords"
          languages={[site.data.primary_language, ...site.data.additional_languages]}
        />
        <TrackedList
          siteId={site.data.id}
          kind="prompts"
          languages={[site.data.primary_language, ...site.data.additional_languages]}
        />
      </div>
    </>
  );
}

function SiteSettingsCard({ site }: { site: SiteOut }) {
  const { t } = useTranslation("app");
  const tc = useTranslation().t;
  const update = useUpdateSite(site.id);
  const role = useCurrentRole();
  const canEdit = role === "owner" || role === "admin";
  const [arabic, setArabic] = useState(site.additional_languages.includes("ar"));
  const [brandEn, setBrandEn] = useState((site.brand_names.en ?? []).join(", "));
  const [brandAr, setBrandAr] = useState((site.brand_names.ar ?? []).join(", "));
  const [competitors, setCompetitors] = useState(site.competitor_domains.join("\n"));
  const [saved, setSaved] = useState(false);
  const edit =
    <T,>(setter: (v: T) => void) =>
    (v: T) => {
      setSaved(false);
      setter(v);
    };

  const split = (v: string) =>
    v
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
  const save = () =>
    update.mutate(
      {
        additional_languages: arabic ? ["ar"] : [],
        brand_names: { en: split(brandEn), ...(arabic ? { ar: split(brandAr) } : {}) },
        competitor_domains: competitors.split(/[\s,]+/).filter(Boolean),
      },
      { onSuccess: () => setSaved(true) },
    );

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("site.settingsTitle")}</CardTitle>
        <CardDescription>
          {tc(`platforms.${site.platform}`)} · <span dir="ltr">{site.homepage_url}</span>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {update.isError && <Alert tone="error">{errorMessage(update.error, tc)}</Alert>}
        {saved && <Alert tone="success">{tc("saved")}</Alert>}
        <fieldset className="space-y-2" disabled={!canEdit}>
          <legend className="text-sm font-medium">{t("site.languages")}</legend>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked disabled /> {tc("languageNames.en")}{" "}
            <Badge variant="muted">{t("site.primary")}</Badge>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={arabic}
              onChange={(e) => edit(setArabic)(e.target.checked)}
            />{" "}
            {tc("languageNames.ar")}{" "}
            <span className="text-muted-foreground">({t("site.optional")})</span>
          </label>
        </fieldset>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("site.brandEn")} hint={t("site.brandHint")}>
            <Input
              value={brandEn}
              onChange={(e) => edit(setBrandEn)(e.target.value)}
              disabled={!canEdit}
            />
          </Field>
          {arabic && (
            <Field label={t("site.brandAr")} hint={t("site.brandHint")}>
              <Input
                value={brandAr}
                onChange={(e) => edit(setBrandAr)(e.target.value)}
                dir="rtl"
                lang="ar"
                disabled={!canEdit}
              />
            </Field>
          )}
        </div>
        <Field label={<Jargon term="competitor">{t("site.competitors")}</Jargon>}>
          <Textarea
            value={competitors}
            onChange={(e) => edit(setCompetitors)(e.target.value)}
            dir="ltr"
            disabled={!canEdit}
          />
        </Field>
        {canEdit && (
          <div className="flex justify-end">
            <Button onClick={save} loading={update.isPending}>
              {tc("save")}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function TrackedList({
  siteId,
  kind,
  languages,
}: {
  siteId: string;
  kind: "keywords" | "prompts";
  languages: string[];
}) {
  const { t } = useTranslation("app");
  const tc = useTranslation().t;
  const qc = useQueryClient();
  const keywords = useKeywords(kind === "keywords" ? siteId : undefined);
  const prompts = usePrompts(kind === "prompts" ? siteId : undefined);
  const query = kind === "keywords" ? keywords : prompts;
  const role = useCurrentRole();
  const canEdit = role !== undefined && role !== "viewer";
  const [draft, setDraft] = useState("");
  const [lang, setLang] = useState(languages[0] ?? "en");
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: [kind] });
    void qc.invalidateQueries({ queryKey: ["org"] });
  };
  const add = useMutation({
    mutationFn: () =>
      api(`/sites/${siteId}/${kind}`, {
        method: "POST",
        body: {
          items: [
            kind === "keywords"
              ? { keyword: draft, language: lang }
              : { prompt_text: draft, language: lang },
          ],
        },
      }),
    onSuccess: () => {
      setDraft("");
      invalidate();
    },
  });
  const act = useMutation({
    mutationFn: ({
      id,
      action,
      status,
    }: {
      id: string;
      action: "status" | "delete";
      status?: string;
    }) =>
      action === "delete"
        ? api(`/sites/${siteId}/${kind}/${id}`, { method: "DELETE" })
        : api(`/sites/${siteId}/${kind}/${id}`, { method: "PATCH", body: { status } }),
    onSuccess: invalidate,
  });
  const rows = (query.data ?? []).map((r) => ({
    id: r.id,
    status: r.status,
    language: r.language,
    text: "keyword" in r ? r.keyword : r.prompt_text,
  }));
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <Jargon term={kind === "keywords" ? "keyword" : "aiPrompt"}>
            {t(`site.${kind}Title`)}
          </Jargon>
        </CardTitle>
        <CardDescription>{t(`site.${kind}Description`)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {(add.isError || act.isError) && (
          <Alert tone="error">{errorMessage(add.error ?? act.error, tc)}</Alert>
        )}
        {query.isPending ? (
          <PageLoader />
        ) : query.isError ? (
          <ErrorState error={query.error} />
        ) : (
          <ul className="divide-y rounded-md border">
            {rows.length === 0 && (
              <li className="text-muted-foreground p-6 text-center text-sm">
                {t("site.emptyList")}
              </li>
            )}
            {rows.map((r) => (
              <li key={r.id} className="flex items-center gap-3 px-3 py-2">
                <span className="flex-1 text-sm" dir="auto" lang={r.language}>
                  {r.text}
                </span>
                <Badge variant="muted">{tc(`languageNames.${r.language}`)}</Badge>
                {r.status === "paused" && <Badge variant="warning">{t("site.paused")}</Badge>}
                {canEdit && (
                  <>
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label={r.status === "active" ? t("site.pause") : t("site.resume")}
                      onClick={() =>
                        act.mutate({
                          id: r.id,
                          action: "status",
                          status: r.status === "active" ? "paused" : "active",
                        })
                      }
                    >
                      {r.status === "active" ? (
                        <Pause className="size-4" />
                      ) : (
                        <Play className="rtl-flip size-4" />
                      )}
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label={tc("remove")}
                      onClick={() => act.mutate({ id: r.id, action: "delete" })}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
        {canEdit && (
          <form
            className="flex flex-col gap-2 sm:flex-row"
            onSubmit={(e) => {
              e.preventDefault();
              if (draft.trim()) add.mutate();
            }}
          >
            <Input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              dir="auto"
              placeholder={t(`site.${kind}Placeholder`)}
            />
            {languages.length > 1 && (
              <Select
                value={lang}
                onChange={(e) => setLang(e.target.value)}
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
            <Button
              type="submit"
              variant="outline"
              loading={add.isPending}
              disabled={!draft.trim()}
            >
              {tc("add")}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
