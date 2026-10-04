import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input, Select } from "@/components/ui/input";
import { PageLoader } from "@/components/ui/spinner";
import { ErrorState, PageHeader } from "@/components/ui/states";
import { api } from "@/lib/api";
import type { OrgSummary } from "@/lib/api-types";
import { CONTACT_EMAIL } from "@/lib/config";
import { errorMessage } from "@/lib/errors";
import { applyLanguage, formatDate, formatNumber, SUPPORTED_LANGUAGES } from "@/lib/i18n";
import { saveUiLanguage, useInvitations, useMembers, useOrg } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { useCurrentRole, useSession } from "@/stores/session";

const TABS = ["profile", "organization", "team"] as const;

export function SettingsPage() {
  const { t } = useTranslation("settings");
  const [tab, setTab] = useState<(typeof TABS)[number]>("profile");
  return (
    <>
      <PageHeader title={t("title")} />
      <div role="tablist" className="mb-6 flex gap-1 border-b">
        {TABS.map((k) => (
          <button
            key={k}
            role="tab"
            aria-selected={tab === k}
            onClick={() => setTab(k)}
            className={cn(
              "-mb-px border-b-2 px-4 py-2 text-sm font-medium",
              tab === k
                ? "border-primary text-primary"
                : "text-muted-foreground hover:text-foreground border-transparent",
            )}
          >
            {t(`tabs.${k}`)}
          </button>
        ))}
      </div>
      {tab === "profile" && <ProfileTab />}
      {tab === "organization" && <OrganizationTab />}
      {tab === "team" && <TeamTab />}
    </>
  );
}

function ProfileTab() {
  const { t, i18n } = useTranslation("settings");
  const tc = useTranslation().t;
  const user = useSession((s) => s.user)!;
  const setUser = useSession((s) => s.setUser);
  const [name, setName] = useState(user.full_name);
  const save = useMutation({
    mutationFn: () => api<typeof user>("/auth/me", { method: "PATCH", body: { full_name: name } }),
    onSuccess: setUser,
  });
  const changeLanguage = async (lang: string) => {
    await applyLanguage(lang);
    await saveUiLanguage(lang);
  };
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{t("profile.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {save.isSuccess && <Alert tone="success">{tc("saved")}</Alert>}
          {save.isError && <Alert tone="error">{errorMessage(save.error, tc)}</Alert>}
          <Field label={t("profile.name")}>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label={t("profile.email")}>
            <Input value={user.email} disabled dir="ltr" />
          </Field>
          {!user.email_verified && <Alert tone="warning">{t("profile.unverified")}</Alert>}
          <div className="flex justify-end">
            <Button onClick={() => save.mutate()} loading={save.isPending}>
              {tc("save")}
            </Button>
          </div>
        </CardContent>
      </Card>
      {SUPPORTED_LANGUAGES.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle>{t("profile.languageTitle")}</CardTitle>
            <CardDescription>{t("profile.languageDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            <Field label={t("profile.language")}>
              <Select
                value={i18n.language}
                onChange={(e) => void changeLanguage(e.target.value)}
                className="max-w-xs"
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l} value={l}>
                    {tc("language.name", { lng: l })}
                  </option>
                ))}
              </Select>
            </Field>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function OrganizationTab() {
  const { t } = useTranslation("settings");
  const tc = useTranslation().t;
  const org = useOrg();
  const role = useCurrentRole();
  const qc = useQueryClient();
  const { orgs, setOrgs } = useSession();
  const [name, setName] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: (value: string) => api("/org", { method: "PATCH", body: { name: value } }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["org"] });
      setOrgs(await api<OrgSummary[]>("/orgs"));
    },
  });
  if (org.isPending) return <PageLoader />;
  if (org.isError) return <ErrorState error={org.error} onRetry={() => void org.refetch()} />;
  const { plan, usage } = org.data;
  const canEdit = role === "owner" || role === "admin";
  const meters = [
    { key: "sites", used: usage.sites, max: plan.max_sites },
    { key: "keywords", used: usage.keywords, max: plan.max_keywords },
    { key: "prompts", used: usage.prompts, max: plan.max_prompts },
  ];
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{t("org.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {save.isError && <Alert tone="error">{errorMessage(save.error, tc)}</Alert>}
          <Field label={t("org.name")}>
            <Input
              value={name ?? org.data.name}
              onChange={(e) => setName(e.target.value)}
              disabled={!canEdit}
            />
          </Field>
          {canEdit && (
            <div className="flex justify-end">
              <Button onClick={() => save.mutate(name ?? org.data.name)} loading={save.isPending}>
                {tc("save")}
              </Button>
            </div>
          )}
          <p className="text-muted-foreground text-xs">
            {t("org.memberOf", { count: orgs.length })}
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {t("plan.title")} <Badge>{plan.name}</Badge>
          </CardTitle>
          <CardDescription>{t("plan.description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {meters.map((m) => (
            <div key={m.key}>
              <div className="mb-1 flex justify-between text-sm">
                <span>{t(`plan.${m.key}`)}</span>
                <span className="text-muted-foreground">
                  {formatNumber(m.used)} / {formatNumber(m.max)}
                </span>
              </div>
              <div
                className="bg-muted h-2 rounded-full"
                role="progressbar"
                aria-valuenow={m.used}
                aria-valuemax={m.max}
                aria-label={t(`plan.${m.key}`)}
              >
                <div
                  className="bg-primary h-2 rounded-full"
                  style={{ width: `${Math.min(100, (m.used / Math.max(1, m.max)) * 100)}%` }}
                />
              </div>
            </div>
          ))}
          <p className="text-sm">
            {t("plan.contact")}{" "}
            <a className="text-primary hover:underline" href={`mailto:${CONTACT_EMAIL}`}>
              {CONTACT_EMAIL}
            </a>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function TeamTab() {
  const { t } = useTranslation("settings");
  const tc = useTranslation().t;
  const role = useCurrentRole();
  const me = useSession((s) => s.user);
  const isAdmin = role === "owner" || role === "admin";
  const members = useMembers();
  const invitations = useInvitations(isAdmin);
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["members"] });
    void qc.invalidateQueries({ queryKey: ["invitations"] });
  };
  const invite = useMutation({
    mutationFn: () =>
      api("/org/invitations", { method: "POST", body: { email, role: inviteRole } }),
    onSuccess: () => {
      setEmail("");
      refresh();
    },
  });
  const change = useMutation({
    mutationFn: ({ id, newRole }: { id: string; newRole: string }) =>
      api(`/org/members/${id}`, { method: "PATCH", body: { role: newRole } }),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api(`/org/members/${id}`, { method: "DELETE" }),
    onSuccess: refresh,
  });
  const revoke = useMutation({
    mutationFn: (id: string) => api(`/org/invitations/${id}`, { method: "DELETE" }),
    onSuccess: refresh,
  });
  const err = invite.error ?? change.error ?? remove.error ?? revoke.error;
  const roles =
    role === "owner" ? ["owner", "admin", "member", "viewer"] : ["admin", "member", "viewer"];
  return (
    <div className="space-y-6">
      {err && <Alert tone="error">{errorMessage(err, tc)}</Alert>}
      <Card>
        <CardHeader>
          <CardTitle>{t("team.members")}</CardTitle>
          <CardDescription>{t("team.rolesHelp")}</CardDescription>
        </CardHeader>
        <CardContent>
          {members.isPending ? (
            <PageLoader />
          ) : members.isError ? (
            <ErrorState error={members.error} />
          ) : (
            <ul className="divide-y">
              {members.data.map((m) => (
                <li key={m.id} className="flex flex-wrap items-center gap-3 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">
                      {m.full_name}
                      {m.user_id === me?.id && ` (${t("team.you")})`}
                    </p>
                    <p className="text-muted-foreground text-sm" dir="ltr">
                      {m.email}
                    </p>
                  </div>
                  {isAdmin && (role === "owner" || m.role !== "owner") ? (
                    <Select
                      value={m.role}
                      className="w-32"
                      aria-label={t("team.role")}
                      onChange={(e) => change.mutate({ id: m.id, newRole: e.target.value })}
                    >
                      {roles.map((r) => (
                        <option key={r} value={r}>
                          {tc(`roles.${r}`)}
                        </option>
                      ))}
                    </Select>
                  ) : (
                    <Badge variant="muted">{tc(`roles.${m.role}`)}</Badge>
                  )}
                  {(isAdmin || m.user_id === me?.id) && (
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label={tc("remove")}
                      onClick={() => remove.mutate(m.id)}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      {isAdmin && (
        <Card>
          <CardHeader>
            <CardTitle>{t("team.invite")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {invite.isSuccess && <Alert tone="success">{t("team.invited")}</Alert>}
            <form
              className="flex flex-col gap-2 sm:flex-row"
              onSubmit={(e) => {
                e.preventDefault();
                invite.mutate();
              }}
            >
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                dir="ltr"
                aria-label={t("team.email")}
              />
              <Select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className="sm:w-36"
                aria-label={t("team.role")}
              >
                {["admin", "member", "viewer"].map((r) => (
                  <option key={r} value={r}>
                    {tc(`roles.${r}`)}
                  </option>
                ))}
              </Select>
              <Button type="submit" loading={invite.isPending} disabled={!email}>
                {t("team.send")}
              </Button>
            </form>
            {invitations.data && invitations.data.length > 0 && (
              <ul className="divide-y rounded-md border">
                {invitations.data.map((i) => (
                  <li key={i.id} className="flex items-center gap-3 px-3 py-2 text-sm">
                    <span className="flex-1" dir="ltr">
                      {i.email}
                    </span>
                    <Badge variant="muted">{tc(`roles.${i.role}`)}</Badge>
                    <span className="text-muted-foreground">
                      {t("team.expires", { date: formatDate(i.expires_at) })}
                    </span>
                    <Button size="sm" variant="ghost" onClick={() => revoke.mutate(i.id)}>
                      {t("team.revoke")}
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
