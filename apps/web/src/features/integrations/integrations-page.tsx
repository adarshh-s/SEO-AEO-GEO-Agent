import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Copy,
  Globe,
  Key,
  Plug,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Webhook,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PageLoader } from "@/components/ui/spinner";
import { EmptyState, ErrorState, PageHeader } from "@/components/ui/states";
import type { ApiKeyCreatedOut } from "@/lib/api-types";
import {
  useApiKeys,
  useCreateApiKey,
  useCreateWebhook,
  useDeleteApiKey,
  useDeleteWebhook,
  useSites,
  useSnippetInfo,
  useVerification,
  useVerifySite,
  useWebhooks,
} from "@/lib/queries";

export function IntegrationsPage() {
  const { t } = useTranslation("app");
  const sites = useSites();
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const siteId = selectedSiteId ?? sites.data?.[0]?.id;

  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState<string>("wordpress");

  // Verification & Snippet queries
  const verification = useVerification(siteId);
  const verifySite = useVerifySite(siteId ?? "");
  const snippetInfo = useSnippetInfo(siteId);

  // API Keys & Webhooks queries
  const apiKeys = useApiKeys();
  const createApiKey = useCreateApiKey();
  const deleteApiKey = useDeleteApiKey();

  const webhooks = useWebhooks();
  const createWebhook = useCreateWebhook();
  const deleteWebhook = useDeleteWebhook();

  // Modals state
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [keyScopes, setKeyScopes] = useState<string[]>(["fixes:read", "fixes:deploy"]);
  const [createdKeyData, setCreatedKeyData] = useState<ApiKeyCreatedOut | null>(null);

  const [showWebhookModal, setShowWebhookModal] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookEvents, setWebhookEvents] = useState<string[]>([
    "fix.created",
    "fix.approved",
    "fix.deployed",
  ]);

  if (sites.isPending) return <PageLoader />;
  if (sites.isError) return <ErrorState error={sites.error} onRetry={() => void sites.refetch()} />;

  if (!sites.data || sites.data.length === 0) {
    return (
      <EmptyState
        icon={Plug}
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

  const handleCopy = (id: string, text: string) => {
    void navigator.clipboard.writeText(text);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleCreateApiKey = () => {
    if (!keyName.trim()) return;
    createApiKey.mutate(
      { name: keyName, scopes: keyScopes },
      {
        onSuccess: (data) => {
          setShowKeyModal(false);
          setCreatedKeyData(data);
          setKeyName("");
        },
      },
    );
  };

  const handleCreateWebhook = () => {
    if (!webhookUrl.trim()) return;
    createWebhook.mutate(
      { url: webhookUrl, events: webhookEvents },
      {
        onSuccess: () => {
          setShowWebhookModal(false);
          setWebhookUrl("");
        },
      },
    );
  };

  const isVerified = verification.data?.verified ?? false;

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader title={t("integrations.title")} description={t("integrations.description")} />

        {sites.data.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-sm font-medium">
              {t("overview.sites")}:
            </span>
            <select
              value={siteId}
              onChange={(e) => setSelectedSiteId(e.target.value)}
              className="border-input bg-background focus-visible:ring-ring rounded-md border px-3 py-1.5 text-sm focus-visible:ring-2 focus-visible:outline-none"
            >
              {sites.data.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name || s.domain}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* 1. Ownership Verification Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-indigo-600" />
              <CardTitle className="text-base font-semibold">
                {t("integrations.verificationTitle")}
              </CardTitle>
            </div>
            <Badge variant={isVerified ? "success" : "warning"} className="w-fit">
              {isVerified ? (
                <>
                  <CheckCircle2 className="me-1 h-3.5 w-3.5" />
                  {t("integrations.verified")}
                </>
              ) : (
                <>
                  <AlertTriangle className="me-1 h-3.5 w-3.5" />
                  {t("integrations.notVerified")}
                </>
              )}
            </Badge>
          </div>
          <CardDescription className="text-xs">
            {t("integrations.verificationDesc")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {verification.isPending && <PageLoader />}
          {verification.data && (
            <>
              {/* Option 1: Meta Tag */}
              <div className="border-border bg-muted/20 space-y-2 rounded-lg border p-3.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold">{t("integrations.metaOption")}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => handleCopy("meta", verification.data.meta_tag)}
                  >
                    {copiedKey === "meta" ? (
                      <>
                        <Check className="me-1 h-3 w-3 text-emerald-600" />
                        {t("fixes.copied")}
                      </>
                    ) : (
                      <>
                        <Copy className="me-1 h-3 w-3" />
                        {t("fixes.copySchema")}
                      </>
                    )}
                  </Button>
                </div>
                <p className="text-muted-foreground text-xs">{t("integrations.metaHint")}</p>
                <pre className="border-border bg-muted/60 overflow-auto rounded-md border p-2.5 font-mono text-xs select-all">
                  {verification.data.meta_tag}
                </pre>
              </div>

              {/* Option 2: DNS TXT */}
              <div className="border-border bg-muted/20 space-y-2 rounded-lg border p-3.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold">{t("integrations.dnsOption")}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => handleCopy("dns", verification.data.dns_txt_record)}
                  >
                    {copiedKey === "dns" ? (
                      <>
                        <Check className="me-1 h-3 w-3 text-emerald-600" />
                        {t("fixes.copied")}
                      </>
                    ) : (
                      <>
                        <Copy className="me-1 h-3 w-3" />
                        {t("fixes.copySchema")}
                      </>
                    )}
                  </Button>
                </div>
                <p className="text-muted-foreground text-xs">{t("integrations.dnsHint")}</p>
                <pre className="border-border bg-muted/60 overflow-auto rounded-md border p-2.5 font-mono text-xs select-all">
                  {verification.data.dns_txt_record}
                </pre>
              </div>

              {verifySite.isError && (
                <Alert tone="error">
                  <p className="font-semibold">Verification check failed</p>
                  <p>
                    We could not find the meta tag or DNS TXT record on your site. Please ensure it
                    is published, purge any CDN/caching layer, and try again.
                  </p>
                </Alert>
              )}

              {verifySite.isSuccess && (
                <Alert tone="success">
                  <p className="font-semibold">Verification Successful</p>
                  <p>{verifySite.data?.message}</p>
                </Alert>
              )}

              {!isVerified && (
                <Button
                  variant="default"
                  onClick={() => verifySite.mutate()}
                  disabled={verifySite.isPending}
                  className="w-full sm:w-auto"
                >
                  <RefreshCw
                    className={`me-2 h-4 w-4 ${verifySite.isPending ? "animate-spin" : ""}`}
                  />
                  {verifySite.isPending ? t("integrations.verifying") : t("integrations.verifyNow")}
                </Button>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* 2. Universal JavaScript Snippet Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-blue-600" />
            <CardTitle className="text-base font-semibold">
              {t("integrations.snippetTitle")}
            </CardTitle>
          </div>
          <CardDescription className="text-xs">{t("integrations.snippetDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {snippetInfo.isPending && <PageLoader />}
          {snippetInfo.data && (
            <>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground text-xs font-semibold">Script Tag</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => handleCopy("snippet", snippetInfo.data.snippet_tag)}
                  >
                    {copiedKey === "snippet" ? (
                      <>
                        <Check className="me-1 h-3 w-3 text-emerald-600" />
                        {t("fixes.copied")}
                      </>
                    ) : (
                      <>
                        <Copy className="me-1 h-3 w-3" />
                        {t("integrations.copySnippet")}
                      </>
                    )}
                  </Button>
                </div>
                <pre className="border-border bg-muted/60 overflow-auto rounded-md border p-3 font-mono text-xs select-all">
                  {snippetInfo.data.snippet_tag}
                </pre>
              </div>

              {/* Platform Guides Tabs */}
              <div className="space-y-3">
                <span className="text-muted-foreground text-xs font-semibold">
                  {t("integrations.platformGuide")}
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {Object.keys(snippetInfo.data.instructions).map((platform) => (
                    <Button
                      key={platform}
                      variant={selectedPlatform === platform ? "default" : "outline"}
                      size="sm"
                      className="h-7 text-xs capitalize"
                      onClick={() => setSelectedPlatform(platform)}
                    >
                      {platform}
                    </Button>
                  ))}
                </div>
                <div className="border-border bg-muted/20 text-foreground rounded-lg border p-3.5 text-xs leading-relaxed">
                  {snippetInfo.data.instructions[selectedPlatform]}
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* 3. API Keys & Webhooks Section */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* API Keys Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
            <div>
              <div className="flex items-center gap-1.5">
                <Key className="h-4 w-4 text-emerald-600" />
                <CardTitle className="text-sm font-semibold">
                  {t("integrations.apiKeysTitle")}
                </CardTitle>
              </div>
              <CardDescription className="mt-1 text-xs">
                {t("integrations.apiKeysDesc")}
              </CardDescription>
            </div>
            <Button size="sm" variant="outline" onClick={() => setShowKeyModal(true)}>
              <Plus className="me-1 h-3.5 w-3.5" />
              {t("integrations.createApiKey")}
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {apiKeys.isPending && <PageLoader />}
            {apiKeys.data?.length === 0 && (
              <p className="text-muted-foreground py-4 text-center text-xs">
                No API keys created yet.
              </p>
            )}
            {apiKeys.data?.map((k) => (
              <div
                key={k.id}
                className="border-border flex items-center justify-between rounded-md border p-2.5 text-xs"
              >
                <div>
                  <div className="text-foreground font-semibold">{k.name}</div>
                  <div className="text-muted-foreground font-mono text-[11px]">
                    {k.prefix}••••••••
                  </div>
                  <div className="mt-1 flex gap-1">
                    {k.scopes.map((s) => (
                      <Badge key={s} variant="outline" className="px-1 py-0 text-[10px]">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteApiKey.mutate(k.id)}
                  disabled={deleteApiKey.isPending}
                  className="text-destructive hover:bg-destructive/10 h-7 w-7 p-0"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Webhooks Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
            <div>
              <div className="flex items-center gap-1.5">
                <Webhook className="h-4 w-4 text-purple-600" />
                <CardTitle className="text-sm font-semibold">
                  {t("integrations.webhooksTitle")}
                </CardTitle>
              </div>
              <CardDescription className="mt-1 text-xs">
                {t("integrations.webhooksDesc")}
              </CardDescription>
            </div>
            <Button size="sm" variant="outline" onClick={() => setShowWebhookModal(true)}>
              <Plus className="me-1 h-3.5 w-3.5" />
              {t("integrations.addWebhook")}
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {webhooks.isPending && <PageLoader />}
            {webhooks.data?.length === 0 && (
              <p className="text-muted-foreground py-4 text-center text-xs">
                No webhooks configured yet.
              </p>
            )}
            {webhooks.data?.map((wh) => (
              <div
                key={wh.id}
                className="border-border flex items-center justify-between rounded-md border p-2.5 text-xs"
              >
                <div className="max-w-[240px] truncate">
                  <div className="text-foreground truncate font-semibold">{wh.url}</div>
                  <div className="text-muted-foreground mt-0.5 text-[11px]">
                    Status: <span className="font-medium text-emerald-600">{wh.status}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {wh.events.map((ev) => (
                      <Badge key={ev} variant="outline" className="px-1 py-0 text-[10px]">
                        {ev}
                      </Badge>
                    ))}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteWebhook.mutate(wh.id)}
                  disabled={deleteWebhook.isPending}
                  className="text-destructive hover:bg-destructive/10 h-7 w-7 shrink-0 p-0"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Modal: Create API Key */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
          <Card className="w-full max-w-md shadow-xl">
            <CardHeader>
              <CardTitle className="text-base">{t("integrations.createApiKey")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-muted-foreground text-xs font-semibold">
                  {t("integrations.keyName")}
                </label>
                <Input
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  placeholder="e.g. Next.js Production"
                  className="mt-1 text-sm"
                />
              </div>

              <div>
                <label className="text-muted-foreground text-xs font-semibold">
                  {t("integrations.scopes")}
                </label>
                <div className="mt-2 space-y-1.5 text-xs">
                  {["fixes:read", "fixes:deploy", "*"].map((sc) => (
                    <label key={sc} className="flex cursor-pointer items-center gap-2">
                      <input
                        type="checkbox"
                        checked={keyScopes.includes(sc)}
                        onChange={(e) => {
                          if (e.target.checked) setKeyScopes([...keyScopes, sc]);
                          else setKeyScopes(keyScopes.filter((s) => s !== sc));
                        }}
                        className="rounded"
                      />
                      <span>{sc}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button variant="ghost" size="sm" onClick={() => setShowKeyModal(false)}>
                  Cancel
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleCreateApiKey}
                  disabled={createApiKey.isPending || !keyName.trim()}
                >
                  Create Key
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Modal: Reveal Raw Key */}
      {createdKeyData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
          <Card className="w-full max-w-md shadow-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-1.5 text-base text-emerald-600">
                <CheckCircle2 className="h-4 w-4" />
                API Key Generated
              </CardTitle>
              <CardDescription className="text-xs">
                {t("integrations.createdKeyNotice")}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border-border bg-muted/60 flex items-center justify-between rounded-md border p-2.5 font-mono text-xs">
                <span className="truncate">{createdKeyData.raw_key}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleCopy("raw-key", createdKeyData.raw_key)}
                  className="ms-2 h-7 shrink-0"
                >
                  {copiedKey === "raw-key" ? (
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </Button>
              </div>

              <div className="flex justify-end pt-2">
                <Button variant="default" size="sm" onClick={() => setCreatedKeyData(null)}>
                  I have saved this key
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Modal: Add Webhook */}
      {showWebhookModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
          <Card className="w-full max-w-md shadow-xl">
            <CardHeader>
              <CardTitle className="text-base">{t("integrations.addWebhook")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-muted-foreground text-xs font-semibold">
                  {t("integrations.webhookUrl")}
                </label>
                <Input
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  placeholder="https://api.yourdomain.com/webhooks"
                  className="mt-1 text-sm"
                />
              </div>

              <div>
                <label className="text-muted-foreground text-xs font-semibold">
                  {t("integrations.subscribedEvents")}
                </label>
                <div className="mt-2 space-y-1.5 text-xs">
                  {["fix.created", "fix.approved", "fix.deployed"].map((ev) => (
                    <label key={ev} className="flex cursor-pointer items-center gap-2">
                      <input
                        type="checkbox"
                        checked={webhookEvents.includes(ev)}
                        onChange={(e) => {
                          if (e.target.checked) setWebhookEvents([...webhookEvents, ev]);
                          else setWebhookEvents(webhookEvents.filter((item) => item !== ev));
                        }}
                        className="rounded"
                      />
                      <span>{ev}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button variant="ghost" size="sm" onClick={() => setShowWebhookModal(false)}>
                  Cancel
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleCreateWebhook}
                  disabled={createWebhook.isPending || !webhookUrl.trim()}
                >
                  Register Webhook
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
