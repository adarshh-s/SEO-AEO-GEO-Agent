import { T } from "@/components/ui/t";
import { useSelectedSite } from "@/lib/use-selected-site";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Copy,
  Download,
  Globe,
  Key,
  Layers,
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
import type { ApiKeyCreatedOut, WebhookCreatedOut, WebhookEvent } from "@/lib/api-types";
import { BRAND, PRODUCT_NAME } from "@/lib/brand";
import {
  useApiKeys,
  useConnectGsc,
  useCreateApiKey,
  useCreateSiteIntegration,
  useCreateWebhook,
  useDeleteApiKey,
  useDeleteSiteIntegration,
  useDeleteWebhook,
  useGscPerformance,
  useSiteIntegrations,
  useSites,
  useSnippetInfo,
  useTestSiteIntegration,
  useVerification,
  useVerifySite,
  useWebhooks,
} from "@/lib/queries";

export function IntegrationsPage() {
  const { t } = useTranslation("app");
  const sites = useSites();
  const [selectedSiteId, setSelectedSiteId] = useSelectedSite();
  const siteId = selectedSiteId;

  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState<string>("wordpress");
  const [deepPlatformTab, setDeepPlatformTab] = useState<string>("wordpress");

  // Verification & Snippet queries
  const verification = useVerification(siteId);
  const verifySite = useVerifySite(siteId ?? "");
  const snippetInfo = useSnippetInfo(siteId);

  // Deep Integrations queries
  const siteIntegrations = useSiteIntegrations(siteId);
  const createIntegration = useCreateSiteIntegration(siteId);
  const deleteIntegration = useDeleteSiteIntegration(siteId);
  const testIntegration = useTestSiteIntegration(siteId);
  const connectGsc = useConnectGsc(siteId);

  // Form states for deep integrations
  const [wpUrl, setWpUrl] = useState("");
  const [wpUser, setWpUser] = useState("");
  const [wpPass, setWpPass] = useState("");

  const [shopifyDomain, setShopifyDomain] = useState("");
  const [shopifyToken, setShopifyToken] = useState("");

  const [ghOwner, setGhOwner] = useState("");
  const [ghRepo, setGhRepo] = useState("");
  const [ghBranch, setGhBranch] = useState("main");
  const [ghToken, setGhToken] = useState("");

  const [gscProperty, setGscProperty] = useState("");

  const [sallaMerchantId, setSallaMerchantId] = useState("");
  const [sallaToken, setSallaToken] = useState("");

  const [zidStoreId, setZidStoreId] = useState("");
  const [zidAccessToken, setZidAccessToken] = useState("");
  const [zidManagerToken, setZidManagerToken] = useState("");

  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);

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
  const [webhookEvents, setWebhookEvents] = useState<WebhookEvent[]>([
    "fix.proposed",
    "fix.approved",
    "fix.deployed",
  ]);
  const [createdWebhook, setCreatedWebhook] = useState<WebhookCreatedOut | null>(null);

  const activeIntegration = siteIntegrations.data?.find((i) => i.provider === deepPlatformTab);
  const gscInteg = siteIntegrations.data?.find((i) => i.provider === "google_search_console");
  const gscPerformance = useGscPerformance(siteId, !!gscInteg && gscInteg.status === "active");

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
      { name: keyName.trim(), scopes: keyScopes },
      {
        onSuccess: (data) => {
          setCreatedKeyData(data);
          setKeyName("");
        },
      },
    );
  };

  const handleCreateWebhook = () => {
    if (!webhookUrl.trim()) return;
    createWebhook.mutate(
      { url: webhookUrl.trim(), events: webhookEvents },
      {
        onSuccess: (data) => {
          // Keep the dialog open to show the signing secret once.
          setCreatedWebhook(data);
          setWebhookUrl("");
        },
      },
    );
  };

  const handleSaveIntegration = (provider: string) => {
    let config: Record<string, unknown> = {};
    let credentials: Record<string, unknown> = {};

    if (provider === "wordpress") {
      config = { site_url: wpUrl || `https://${sites.data?.find((s) => s.id === siteId)?.domain}` };
      credentials = { username: wpUser, application_password: wpPass };
    } else if (provider === "shopify") {
      config = { shop_domain: shopifyDomain };
      credentials = { access_token: shopifyToken };
    } else if (provider === "github") {
      config = { repo_owner: ghOwner, repo_name: ghRepo, base_branch: ghBranch || "main" };
      credentials = { token: ghToken };
    } else if (provider === "salla") {
      config = { mode: sallaToken ? "app" : "snippet" };
      credentials = sallaToken ? { access_token: sallaToken, merchant_id: sallaMerchantId } : {};
    } else if (provider === "zid") {
      config = { mode: zidAccessToken ? "app" : "snippet" };
      credentials = zidAccessToken
        ? { access_token: zidAccessToken, manager_token: zidManagerToken, store_id: zidStoreId }
        : {};
    }

    createIntegration.mutate(
      { provider, config, credentials },
      {
        onSuccess: () => {
          setTestResult({ ok: true, message: "Configuration saved successfully." });
        },
      },
    );
  };

  const handleTestIntegration = (id: string) => {
    testIntegration.mutate(id, {
      onSuccess: (data) => {
        setTestResult({ ok: data.ok, message: data.message });
      },
    });
  };

  const handleConnectGsc = () => {
    const currentSite = sites.data?.find((s) => s.id === siteId);
    const propUrl = gscProperty || currentSite?.homepage_url || `https://${currentSite?.domain}/`;
    connectGsc.mutate(
      {
        code: "sample_oauth_code",
        property_url: propUrl,
        redirect_uri: window.location.origin + "/app/integrations",
      },
      {
        onSuccess: () => {
          setTestResult({ ok: true, message: "Connected to Google Search Console." });
        },
      },
    );
  };

  const currentSite = sites.data.find((s) => s.id === siteId);
  const isVerified = verification.data?.verified || currentSite?.verified_at != null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader title={t("integrations.title")} description={t("integrations.description")} />

        {sites.data.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-xs font-medium">
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
                        {t("integrations.copyCode")}
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
                        {t("integrations.copyCode")}
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
                  <p className="font-semibold">
                    <T k="integrations.verification_check_failed" />
                  </p>
                  <p>
                    <T k="integrations.we_could_not_find_the_meta_tag_or_dns_tx" />
                  </p>
                </Alert>
              )}

              {verifySite.isSuccess && (
                <Alert tone="success">
                  <p className="font-semibold">
                    <T k="integrations.verification_successful" />
                  </p>
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

      {/* 2. Phase 4: Deep Platform Integrations Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-indigo-600" />
            <CardTitle className="text-base font-semibold">
              {t("integrations.deepIntegrationsTitle")}
            </CardTitle>
          </div>
          <CardDescription className="text-xs">
            {t("integrations.deepIntegrationsDesc")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Tabs */}
          <div className="border-border/60 flex flex-wrap gap-1.5 border-b pb-3">
            {[
              { id: "wordpress", label: "WordPress" },
              { id: "shopify", label: "Shopify" },
              { id: "salla", label: "Salla (سلة)" },
              { id: "zid", label: "Zid (زد)" },
              { id: "nextjs", label: "Next.js / SDK" },
              { id: "github", label: "GitHub" },
              { id: "cloudflare", label: "Cloudflare" },
              { id: "google_search_console", label: "Google Search Console" },
            ].map((tab) => (
              <Button
                key={tab.id}
                variant={deepPlatformTab === tab.id ? "default" : "outline"}
                size="sm"
                className="h-8 text-xs"
                onClick={() => {
                  setDeepPlatformTab(tab.id);
                  setTestResult(null);
                }}
              >
                {tab.label}
              </Button>
            ))}
          </div>

          {testResult && (
            <Alert tone={testResult.ok ? "success" : "error"}>
              <p className="font-semibold">
                {testResult.ok ? <T k="integrations.success" /> : <T k="integrations.notice" />}
              </p>
              <p>{testResult.message}</p>
            </Alert>
          )}

          {/* WordPress Tab */}
          {deepPlatformTab === "wordpress" && (
            <div className="space-y-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h4 className="text-sm font-semibold">
                    {PRODUCT_NAME} <T k="integrations.wordpress_plugin" />
                  </h4>
                  <p className="text-muted-foreground text-xs">
                    <T k="integrations.server_side_title_description_schema_inj" />
                  </p>
                </div>
                <Button variant="outline" size="sm" asChild className="h-8 shrink-0 text-xs">
                  <a href={`/api/sites/${siteId}/integrations/wordpress/download`} download>
                    <Download className="me-1 h-3.5 w-3.5" />
                    {t("integrations.downloadPlugin")}
                  </a>
                </Button>
              </div>

              <div className="border-border bg-muted/20 space-y-3 rounded-lg border p-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <label className="text-muted-foreground text-xs font-medium">
                      <T k="integrations.site_rest_url" />
                    </label>
                    <Input
                      placeholder="https://example.com"
                      value={wpUrl}
                      onChange={(e) => setWpUrl(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-muted-foreground text-xs font-medium">
                      <T k="integrations.application_username" />
                    </label>
                    <Input
                      placeholder="admin"
                      value={wpUser}
                      onChange={(e) => setWpUser(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="space-y-1 sm:col-span-2">
                    <label className="text-muted-foreground text-xs font-medium">
                      <T k="integrations.application_password_for_draft_content_c" />
                    </label>
                    <Input
                      type="password"
                      placeholder="abcd efgh ijkl mnop"
                      value={wpPass}
                      onChange={(e) => setWpPass(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <Button
                    size="sm"
                    onClick={() => handleSaveIntegration("wordpress")}
                    disabled={createIntegration.isPending}
                    className="h-8 text-xs"
                  >
                    {t("integrations.saveConfig")}
                  </Button>
                  {activeIntegration && (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTestIntegration(activeIntegration.id)}
                        disabled={testIntegration.isPending}
                        className="h-8 text-xs"
                      >
                        <RefreshCw
                          className={`me-1 h-3 w-3 ${testIntegration.isPending ? "animate-spin" : ""}`}
                        />
                        {t("integrations.testConnection")}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteIntegration.mutate(activeIntegration.id)}
                        disabled={deleteIntegration.isPending}
                        className="text-destructive hover:bg-destructive/10 h-8 text-xs"
                        title={t("integrations.disconnect") ?? "Disconnect"}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Shopify Tab */}
          {deepPlatformTab === "shopify" && (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-semibold">
                  <T k="integrations.shopify_graphql_admin_app_embed" />
                </h4>
                <p className="text-muted-foreground text-xs">
                  <T k="integrations.native_seo_fields_for_products_pages_ser" />
                </p>
              </div>

              <div className="border-border bg-muted/20 space-y-3 rounded-lg border p-4">
                <div className="space-y-1">
                  <label className="text-muted-foreground text-xs font-medium">
                    <T k="integrations.store_domain_myshopify_com" />
                  </label>
                  <Input
                    placeholder="my-store.myshopify.com"
                    value={shopifyDomain}
                    onChange={(e) => setShopifyDomain(e.target.value)}
                    className="text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-muted-foreground text-xs font-medium">
                    <T k="integrations.admin_api_access_token" />
                  </label>
                  <Input
                    type="password"
                    placeholder="shpat_..."
                    value={shopifyToken}
                    onChange={(e) => setShopifyToken(e.target.value)}
                    className="text-xs"
                  />
                </div>

                <div className="flex items-center justify-between pt-2">
                  <Button
                    size="sm"
                    onClick={() => handleSaveIntegration("shopify")}
                    disabled={createIntegration.isPending}
                    className="h-8 text-xs"
                  >
                    {t("integrations.saveConfig")}
                  </Button>
                  {activeIntegration && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestIntegration(activeIntegration.id)}
                      disabled={testIntegration.isPending}
                      className="h-8 text-xs"
                    >
                      {t("integrations.testConnection")}
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Next.js & React SDK Tab */}
          {deepPlatformTab === "nextjs" && (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-semibold">
                  {BRAND.sdk_package} <T k="integrations.for_next_js_react" />
                </h4>
                <p className="text-muted-foreground text-xs">
                  <T k="integrations.first_class_server_side_rendering_for_ap" />
                </p>
              </div>

              <div className="space-y-3">
                <div className="border-border bg-muted/20 rounded-lg border p-3.5">
                  <span className="text-muted-foreground text-xs font-semibold">
                    <T k="integrations.1_install_package" />
                  </span>
                  <pre className="border-border bg-muted/60 mt-2 overflow-auto rounded-md border p-2.5 font-mono text-xs select-all">
                    npm install {BRAND.sdk_package}
                  </pre>
                </div>

                <div className="border-border bg-muted/20 rounded-lg border p-3.5">
                  <span className="text-muted-foreground text-xs font-semibold">
                    <T k="integrations.2_app_router_generatemetadata_schema_com" />
                  </span>
                  <pre className="border-border bg-muted/60 mt-2 overflow-auto rounded-md border p-2.5 font-mono text-xs select-all">
                    {`import { getSeoMetadata, StructuredData } from "${BRAND.sdk_package}";

export async function generateMetadata() {
  return await getSeoMetadata({
    siteKey: "${currentSite?.site_key ?? "YOUR_SITE_KEY"}",
    url: "https://${currentSite?.domain ?? "example.com"}/",
    defaultMetadata: { title: "Home" },
  });
}

export default function Page() {
  return (
    <>
      <StructuredData siteKey="${currentSite?.site_key ?? "YOUR_SITE_KEY"}" url="https://${currentSite?.domain ?? "example.com"}/" />
      <main>Page Content</main>
    </>
  );
}`}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* GitHub Tab */}
          {deepPlatformTab === "github" && (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-semibold">
                  <T k="integrations.automated_github_pull_requests" />
                </h4>
                <p className="text-muted-foreground text-xs">
                  {PRODUCT_NAME} <T k="integrations.patches_target_pages_components_on_an_is" />
                </p>
              </div>

              <div className="border-border bg-muted/20 space-y-3 rounded-lg border p-4">
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="space-y-1">
                    <label className="text-muted-foreground text-xs font-medium">
                      <T k="integrations.repository_owner" />
                    </label>
                    <Input
                      placeholder="acme-corp"
                      value={ghOwner}
                      onChange={(e) => setGhOwner(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-muted-foreground text-xs font-medium">
                      <T k="integrations.repository_name" />
                    </label>
                    <Input
                      placeholder="website"
                      value={ghRepo}
                      onChange={(e) => setGhRepo(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-muted-foreground text-xs font-medium">
                      <T k="integrations.base_branch" />
                    </label>
                    <Input
                      placeholder="main"
                      value={ghBranch}
                      onChange={(e) => setGhBranch(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="text-muted-foreground text-xs font-medium">
                    <T k="integrations.personal_access_token_contents_write_pul" />
                  </label>
                  <Input
                    type="password"
                    placeholder="ghp_..."
                    value={ghToken}
                    onChange={(e) => setGhToken(e.target.value)}
                    className="text-xs"
                  />
                </div>

                <div className="flex items-center justify-between pt-2">
                  <Button
                    size="sm"
                    onClick={() => handleSaveIntegration("github")}
                    disabled={createIntegration.isPending}
                    className="h-8 text-xs"
                  >
                    {t("integrations.saveConfig")}
                  </Button>
                  {activeIntegration && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestIntegration(activeIntegration.id)}
                      disabled={testIntegration.isPending}
                      className="h-8 text-xs"
                    >
                      {t("integrations.testConnection")}
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Cloudflare Tab */}
          {deepPlatformTab === "cloudflare" && (
            <div className="space-y-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h4 className="text-sm font-semibold">
                    <T k="integrations.cloudflare_edge_worker_htmlrewriter" />
                  </h4>
                  <p className="text-muted-foreground text-xs">
                    <T k="integrations.intercepts_html_responses_on_route" /> <code>/*</code>{" "}
                    <T k="integrations.and_injects_approved_metadata_and_schema" />
                  </p>
                </div>
                <Button variant="outline" size="sm" asChild className="h-8 shrink-0 text-xs">
                  <a href={`/api/sites/${siteId}/integrations/cloudflare/worker.js`} download>
                    <Download className="me-1 h-3.5 w-3.5" />
                    {t("integrations.downloadWorker")}
                  </a>
                </Button>
              </div>

              <div className="border-border bg-muted/20 rounded-lg border p-4">
                <p className="text-muted-foreground text-xs leading-relaxed">
                  <T k="integrations.deploy_this_worker_to_your_cloudflare_zo" />{" "}
                  <code>example.com/*</code>
                  <T k="integrations.it_caches_approved_fixes_at_the_edge_and" />
                </p>
              </div>
            </div>
          )}

          {/* Google Search Console Tab */}
          {deepPlatformTab === "google_search_console" && (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-semibold">
                  <T k="integrations.google_search_console_integration" />
                </h4>
                <p className="text-muted-foreground text-xs">
                  <T k="integrations.sync_google_search_performance_metrics_c" />
                </p>
              </div>

              <div className="border-border bg-muted/20 space-y-4 rounded-lg border p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="space-y-1">
                    <span className="text-xs font-medium">
                      <T k="integrations.search_console_property" />
                    </span>
                    <Input
                      placeholder={currentSite?.homepage_url || "https://example.com/"}
                      value={gscProperty}
                      onChange={(e) => setGscProperty(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <Button
                    size="sm"
                    onClick={handleConnectGsc}
                    disabled={connectGsc.isPending}
                    className="h-9 self-end text-xs"
                  >
                    <Plug className="me-1.5 h-3.5 w-3.5" />
                    {t("integrations.connectGsc")}
                  </Button>
                </div>

                {gscInteg && (
                  <Badge variant="success" className="text-xs">
                    <CheckCircle2 className="me-1 h-3.5 w-3.5" />
                    {t("integrations.gscVerifiedOwner")}
                  </Badge>
                )}

                {gscPerformance.data && gscPerformance.data.rows?.length > 0 && (
                  <div className="space-y-2 border-t pt-3">
                    <span className="text-xs font-semibold">
                      {t("integrations.gscPerformance")}
                    </span>
                    <div className="border-border divide-border bg-card divide-y rounded-md border text-xs">
                      {gscPerformance.data.rows.slice(0, 5).map((row, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2.5">
                          <span className="text-foreground font-medium">
                            {row.keys?.[0] || "Query"}
                          </span>
                          <div className="text-muted-foreground flex items-center gap-4">
                            <span>
                              {row.clicks} <T k="integrations.clicks" />
                            </span>
                            <span>
                              {row.impressions} <T k="integrations.impr" />
                            </span>
                            <span>
                              <T k="integrations.pos" /> {row.position?.toFixed(1)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Salla Tab */}
          {deepPlatformTab === "salla" && (
            <div className="space-y-4">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold">
                    <T k="integrations.salla_e_commerce_connector" />
                  </h4>
                  <Badge variant="outline" className="text-[10px] font-bold">
                    <T k="integrations.dual_mode" />
                  </Badge>
                </div>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  <T k="integrations.support_both_direct_partner_app_api_auto" />
                </p>
              </div>

              {/* Mode 1: App API Credentials */}
              <div className="border-border bg-muted/20 space-y-3 rounded-lg border p-4">
                <div className="flex items-center justify-between">
                  <h5 className="text-xs font-semibold">
                    <T k="integrations.option_a_salla_partner_api_integration" />
                  </h5>
                  <Badge variant="muted" className="text-[10px]">
                    <T k="integrations.direct_api" />
                  </Badge>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <label className="text-muted-foreground text-xs font-medium">
                      <T k="integrations.merchant_id" />
                    </label>
                    <Input
                      placeholder="e.g. 12345678"
                      value={sallaMerchantId}
                      onChange={(e) => setSallaMerchantId(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-muted-foreground text-xs font-medium">
                      <T k="integrations.access_token" />
                    </label>
                    <Input
                      type="password"
                      placeholder="Bearer token from Salla Partner Portal"
                      value={sallaToken}
                      onChange={(e) => setSallaToken(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <Button
                    size="sm"
                    onClick={() => handleSaveIntegration("salla")}
                    disabled={createIntegration.isPending}
                    className="h-8 text-xs"
                  >
                    {t("integrations.saveConfig")}
                  </Button>
                  {activeIntegration && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestIntegration(activeIntegration.id)}
                      disabled={testIntegration.isPending}
                      className="h-8 text-xs"
                    >
                      {t("integrations.testConnection")}
                    </Button>
                  )}
                </div>
              </div>

              {/* Mode 2: Twilight Theme Custom Snippet */}
              <div className="border-border bg-muted/20 space-y-3 rounded-lg border p-4">
                <div className="flex items-center justify-between">
                  <h5 className="text-xs font-semibold">
                    <T k="integrations.option_b_salla_twilight_snippet_seo_guid" />
                  </h5>
                  <Badge
                    variant="outline"
                    className="border-emerald-300 text-[10px] text-emerald-600"
                  >
                    <T k="integrations.no_app_review_required" />
                  </Badge>
                </div>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  <T k="integrations.inject_the_tracking_and_verification_scr" />{" "}
                  <strong>
                    <T k="integrations.store_settings_store_options_custom_code" />
                  </strong>
                  :
                </p>
                <div className="relative">
                  <pre className="border-border bg-muted/60 overflow-auto rounded-md border p-3 font-mono text-xs select-all">
                    {`<!-- ${PRODUCT_NAME} SEO & AI Visibility Tag -->
<meta name="${BRAND.verification_meta_name}" content="${siteId ?? "SITE_KEY"}" />
<script defer src="https://${BRAND.brand_slug}.com/${BRAND.snippet_filename}" data-site-key="${siteId ?? "SITE_KEY"}" data-platform="salla"></script>
<!-- End ${PRODUCT_NAME} Tag -->`}
                  </pre>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute end-2 top-2 h-7 text-xs"
                    onClick={() =>
                      handleCopy(
                        "salla-snippet",
                        `<!-- ${PRODUCT_NAME} SEO & AI Visibility Tag -->\n<meta name="${BRAND.verification_meta_name}" content="${siteId ?? "SITE_KEY"}" />\n<script defer src="https://${BRAND.brand_slug}.com/${BRAND.snippet_filename}" data-site-key="${siteId ?? "SITE_KEY"}" data-platform="salla"></script>\n<!-- End ${PRODUCT_NAME} Tag -->`,
                      )
                    }
                  >
                    {copiedKey === "salla-snippet" ? (
                      <Check className="h-3 w-3 text-emerald-600" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                </div>
                <div className="text-muted-foreground space-y-1 border-t pt-2 text-[11px]">
                  <p className="text-foreground font-semibold">
                    <T k="integrations.salla_optimization_steps" />
                  </p>
                  <ol className="list-inside list-decimal space-y-0.5">
                    <li>
                      <T k="integrations.paste_the_snippet_in_salla_twilight_cust" />
                    </li>
                    <li>
                      <T k="integrations.update_product_titles_meta_descriptions_" /> {PRODUCT_NAME}{" "}
                      <T k="integrations.recommendations" />
                    </li>
                    <li>
                      <T k="integrations.dynamic_schema_for_faqs_and_ai_citations" />
                    </li>
                  </ol>
                </div>
              </div>
            </div>
          )}

          {/* Zid Tab */}
          {deepPlatformTab === "zid" && (
            <div className="space-y-4">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold">
                    <T k="integrations.zid_e_commerce_connector" />
                  </h4>
                  <Badge variant="outline" className="text-[10px] font-bold">
                    <T k="integrations.dual_mode" />
                  </Badge>
                </div>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  <T k="integrations.connect_your_zid_store_via_direct_manage" />
                </p>
              </div>

              {/* Mode 1: Zid API Credentials */}
              <div className="border-border bg-muted/20 space-y-3 rounded-lg border p-4">
                <div className="flex items-center justify-between">
                  <h5 className="text-xs font-semibold">
                    <T k="integrations.option_a_zid_partner_api_integration" />
                  </h5>
                  <Badge variant="muted" className="text-[10px]">
                    <T k="integrations.manager_api" />
                  </Badge>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="space-y-1">
                    <label className="text-muted-foreground text-xs font-medium">
                      <T k="integrations.store_id" />
                    </label>
                    <Input
                      placeholder="e.g. 54321"
                      value={zidStoreId}
                      onChange={(e) => setZidStoreId(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-muted-foreground text-xs font-medium">
                      <T k="integrations.access_token" />
                    </label>
                    <Input
                      type="password"
                      placeholder="OAuth Access Token"
                      value={zidAccessToken}
                      onChange={(e) => setZidAccessToken(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-muted-foreground text-xs font-medium">
                      <T k="integrations.manager_token" />
                    </label>
                    <Input
                      type="password"
                      placeholder="Manager Secret Token"
                      value={zidManagerToken}
                      onChange={(e) => setZidManagerToken(e.target.value)}
                      className="text-xs"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <Button
                    size="sm"
                    onClick={() => handleSaveIntegration("zid")}
                    disabled={createIntegration.isPending}
                    className="h-8 text-xs"
                  >
                    {t("integrations.saveConfig")}
                  </Button>
                  {activeIntegration && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestIntegration(activeIntegration.id)}
                      disabled={testIntegration.isPending}
                      className="h-8 text-xs"
                    >
                      {t("integrations.testConnection")}
                    </Button>
                  )}
                </div>
              </div>

              {/* Mode 2: Zid Storefront Custom Scripts */}
              <div className="border-border bg-muted/20 space-y-3 rounded-lg border p-4">
                <div className="flex items-center justify-between">
                  <h5 className="text-xs font-semibold">
                    <T k="integrations.option_b_zid_storefront_script_seo_guide" />
                  </h5>
                  <Badge
                    variant="outline"
                    className="border-emerald-300 text-[10px] text-emerald-600"
                  >
                    <T k="integrations.instant_setup" />
                  </Badge>
                </div>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  <T k="integrations.add_this_snippet_to_your_store_via" />{" "}
                  <strong>
                    <T k="integrations.store_settings_custom_scripts_head" />
                  </strong>
                  :
                </p>
                <div className="relative">
                  <pre className="border-border bg-muted/60 overflow-auto rounded-md border p-3 font-mono text-xs select-all">
                    {`<!-- ${PRODUCT_NAME} SEO & AI Visibility Tag -->
<meta name="${BRAND.verification_meta_name}" content="${siteId ?? "SITE_KEY"}" />
<script defer src="https://${BRAND.brand_slug}.com/${BRAND.snippet_filename}" data-site-key="${siteId ?? "SITE_KEY"}" data-platform="zid"></script>
<!-- End ${PRODUCT_NAME} Tag -->`}
                  </pre>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute end-2 top-2 h-7 text-xs"
                    onClick={() =>
                      handleCopy(
                        "zid-snippet",
                        `<!-- ${PRODUCT_NAME} SEO & AI Visibility Tag -->\n<meta name="${BRAND.verification_meta_name}" content="${siteId ?? "SITE_KEY"}" />\n<script defer src="https://${BRAND.brand_slug}.com/${BRAND.snippet_filename}" data-site-key="${siteId ?? "SITE_KEY"}" data-platform="zid"></script>\n<!-- End ${PRODUCT_NAME} Tag -->`,
                      )
                    }
                  >
                    {copiedKey === "zid-snippet" ? (
                      <Check className="h-3 w-3 text-emerald-600" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                </div>
                <div className="text-muted-foreground space-y-1 border-t pt-2 text-[11px]">
                  <p className="text-foreground font-semibold">
                    <T k="integrations.zid_store_optimization_steps" />
                  </p>
                  <ol className="list-inside list-decimal space-y-0.5">
                    <li>
                      <T k="integrations.paste_the_snippet_into_zid_custom_script" />
                    </li>
                    <li>
                      <T k="integrations.update_your_product_category_seo_details" />
                    </li>
                    <li>
                      <T k="integrations.aeo_and_schema_enhancements_are_automati" />
                    </li>
                  </ol>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 3. Universal JavaScript Snippet Card */}
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
                  <span className="text-muted-foreground text-xs font-semibold">
                    <T k="integrations.script_tag" />
                  </span>
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

              {/* Notice for JS limitations with AI Bots */}
              <div className="border-border space-y-1.5 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-900 dark:text-amber-200">
                <p className="flex items-center gap-1.5 font-semibold">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  <T k="integrations.crawler_capability_note" />
                </p>
                <p className="leading-relaxed">
                  <T k="integrations.the_client_side_javascript_snippet_works" />
                </p>
              </div>

              {/* Platform specific instructions */}
              <div className="border-border bg-muted/20 space-y-3 rounded-lg border p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold">{t("integrations.platformGuide")}</span>
                  <select
                    value={selectedPlatform}
                    onChange={(e) => setSelectedPlatform(e.target.value)}
                    className="border-input bg-background focus-visible:ring-ring rounded-md border px-2.5 py-1 text-xs focus-visible:ring-1 focus-visible:outline-none"
                  >
                    <option value="wordpress">{t("integrations.wordpress", { ns: "ui" })}</option>
                    <option value="shopify">{t("integrations.shopify", { ns: "ui" })}</option>
                    <option value="nextjs">{t("integrations.next_js", { ns: "ui" })}</option>
                    <option value="wix">{t("integrations.wix", { ns: "ui" })}</option>
                    <option value="webflow">{t("integrations.webflow", { ns: "ui" })}</option>
                    <option value="salla">{t("integrations.salla", { ns: "ui" })}</option>
                    <option value="custom">{t("integrations.custom_static", { ns: "ui" })}</option>
                  </select>
                </div>

                <p className="text-muted-foreground text-xs leading-relaxed">
                  {snippetInfo.data.instructions[selectedPlatform] ??
                    snippetInfo.data.instructions["custom"]}
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* 4. Organization API Keys Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <Key className="h-5 w-5 text-amber-600" />
              <CardTitle className="text-base font-semibold">
                {t("integrations.apiKeysTitle")}
              </CardTitle>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setCreatedKeyData(null);
                setShowKeyModal(true);
              }}
              className="w-fit"
            >
              <Plus className="me-1 h-3.5 w-3.5" />
              {t("integrations.createApiKey")}
            </Button>
          </div>
          <CardDescription className="text-xs">{t("integrations.apiKeysDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {apiKeys.isPending && <PageLoader />}
          {apiKeys.isError && (
            <ErrorState error={apiKeys.error} onRetry={() => void apiKeys.refetch()} />
          )}

          {apiKeys.data && apiKeys.data.length === 0 && (
            <p className="text-muted-foreground text-xs">
              <T k="integrations.no_active_api_keys_found" />
            </p>
          )}

          {apiKeys.data && apiKeys.data.length > 0 && (
            <div className="border-border divide-border divide-y rounded-md border">
              {apiKeys.data.map((k) => (
                <div key={k.id} className="flex items-center justify-between p-3 text-xs">
                  <div className="space-y-0.5">
                    <span className="text-foreground font-semibold">{k.name}</span>
                    <div className="text-muted-foreground flex items-center gap-2 font-mono">
                      <span>{k.prefix}...</span>
                      <span>•</span>
                      <span>{k.scopes.join(", ")}</span>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteApiKey.mutate(k.id)}
                    disabled={deleteApiKey.isPending}
                    className="text-destructive hover:bg-destructive/10 h-7 text-xs"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 5. Webhooks Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <Webhook className="h-5 w-5 text-emerald-600" />
              <CardTitle className="text-base font-semibold">
                {t("integrations.webhooksTitle")}
              </CardTitle>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowWebhookModal(true)}
              className="w-fit"
            >
              <Plus className="me-1 h-3.5 w-3.5" />
              {t("integrations.addWebhook")}
            </Button>
          </div>
          <CardDescription className="text-xs">{t("integrations.webhooksDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {webhooks.isPending && <PageLoader />}
          {webhooks.isError && (
            <ErrorState error={webhooks.error} onRetry={() => void webhooks.refetch()} />
          )}

          {webhooks.data && webhooks.data.length === 0 && (
            <p className="text-muted-foreground text-xs">
              <T k="integrations.no_active_webhooks_configured" />
            </p>
          )}

          {webhooks.data && webhooks.data.length > 0 && (
            <div className="border-border divide-border divide-y rounded-md border">
              {webhooks.data.map((wh) => (
                <div key={wh.id} className="flex items-center justify-between p-3 text-xs">
                  <div className="max-w-[80%] space-y-0.5">
                    <span className="text-foreground block truncate font-mono font-semibold">
                      {wh.url}
                    </span>
                    <div className="text-muted-foreground flex flex-wrap items-center gap-1.5">
                      {wh.events.map((ev) => (
                        <Badge key={ev} variant="outline" className="text-[10px]">
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
                    className="text-destructive hover:bg-destructive/10 h-7 text-xs"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal: Create API Key */}
      {showKeyModal && (
        <div className="bg-background/80 fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="border-border bg-card w-full max-w-md space-y-4 rounded-xl border p-5 shadow-lg">
            <h3 className="text-base font-semibold">{t("integrations.createApiKey")}</h3>

            {!createdKeyData ? (
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-muted-foreground text-xs font-medium">
                    {t("integrations.keyName")}
                  </label>
                  <Input
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    placeholder="e.g. CI/CD Deployment Key"
                    className="text-xs"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-muted-foreground text-xs font-medium">
                    {t("integrations.scopes")}
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {["read:fixes", "write:fixes", "admin"].map((scope) => (
                      <label key={scope} className="flex items-center gap-1.5 text-xs">
                        <input
                          type="checkbox"
                          checked={keyScopes.includes(scope)}
                          onChange={(e) => {
                            if (e.target.checked) setKeyScopes([...keyScopes, scope]);
                            else setKeyScopes(keyScopes.filter((s) => s !== scope));
                          }}
                        />
                        <span>{scope}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <Button variant="ghost" size="sm" onClick={() => setShowKeyModal(false)}>
                    {t("common.cancel") ?? "Cancel"}
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleCreateApiKey}
                    disabled={createApiKey.isPending || !keyName.trim()}
                  >
                    {createApiKey.isPending ? (
                      <T k="integrations.creating" />
                    ) : (
                      <T k="integrations.generate_key" />
                    )}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <Alert tone="warning">
                  <p className="text-xs font-semibold">{t("integrations.createdKeyNotice")}</p>
                </Alert>
                <div className="bg-muted/40 flex items-center justify-between rounded-md border p-2">
                  <span className="font-mono text-xs break-all select-all">
                    {createdKeyData.raw_key}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ms-2 h-7 shrink-0 text-xs"
                    onClick={() => handleCopy("raw-key", createdKeyData.raw_key)}
                  >
                    {copiedKey === "raw-key" ? (
                      <Check className="h-3 w-3 text-emerald-600" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                </div>
                <div className="flex justify-end pt-2">
                  <Button size="sm" onClick={() => setShowKeyModal(false)}>
                    {t("common.done") ?? "Done"}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal: Create Webhook */}
      {showWebhookModal && (
        <div className="bg-background/80 fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="border-border bg-card w-full max-w-md space-y-4 rounded-xl border p-5 shadow-lg">
            <h3 className="text-base font-semibold">{t("integrations.addWebhook")}</h3>

            {createdWebhook ? (
              <div className="space-y-3">
                <Alert tone="warning">
                  <p className="text-xs font-semibold">{t("integrations.webhookSecretNotice")}</p>
                </Alert>
                <div className="bg-muted/40 flex items-center justify-between rounded-md border p-2">
                  <span className="font-mono text-xs break-all select-all" dir="ltr">
                    {createdWebhook.secret}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ms-2 h-7 shrink-0 text-xs"
                    onClick={() => handleCopy("webhook-secret", createdWebhook.secret)}
                  >
                    {copiedKey === "webhook-secret" ? (
                      <Check className="h-3 w-3 text-emerald-600" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                </div>
                <div className="flex justify-end pt-2">
                  <Button
                    size="sm"
                    onClick={() => {
                      setCreatedWebhook(null);
                      setShowWebhookModal(false);
                    }}
                  >
                    {t("integrations.done")}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-muted-foreground text-xs font-medium">
                    {t("integrations.webhookUrl")}
                  </label>
                  <Input
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    placeholder="https://example.com/api/webhook"
                    className="text-xs"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-muted-foreground text-xs font-medium">
                    {t("integrations.subscribedEvents")}
                  </label>
                  <div className="flex flex-col gap-1.5">
                    {(
                      [
                        "fix.proposed",
                        "fix.approved",
                        "fix.deployed",
                        "audit.completed",
                        "score.changed",
                      ] as WebhookEvent[]
                    ).map((event) => (
                      <label key={event} className="flex items-center gap-1.5 text-xs">
                        <input
                          type="checkbox"
                          checked={webhookEvents.includes(event)}
                          onChange={(e) => {
                            if (e.target.checked) setWebhookEvents([...webhookEvents, event]);
                            else setWebhookEvents(webhookEvents.filter((ev) => ev !== event));
                          }}
                        />
                        <span>{event}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <Button variant="ghost" size="sm" onClick={() => setShowWebhookModal(false)}>
                    {t("integrations.cancel")}
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleCreateWebhook}
                    disabled={createWebhook.isPending || !webhookUrl.trim()}
                  >
                    {createWebhook.isPending
                      ? t("integrations.addingWebhook")
                      : t("integrations.addWebhook")}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
