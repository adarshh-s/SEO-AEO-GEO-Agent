import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Cpu,
  DollarSign,
  Edit,
  Layers,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldAlert,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { PageLoader } from "@/components/ui/spinner";
import { ErrorState, PageHeader } from "@/components/ui/states";
import { api } from "@/lib/api";
import type { AdminOrgOut, PlanOut } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/i18n";
import {
  useAdminAuditLogs,
  useAdminCostSummary,
  useAdminOrgCosts,
  useAdminOrgs,
  useAdminPlans,
  useAdminResetCounters,
  useAdminUpdatePlan,
} from "@/lib/queries";

export function AdminPage() {
  const { t } = useTranslation("admin");
  const tc = useTranslation().t;
  const qc = useQueryClient();

  const [activeTab, setActiveTab] = useState<"orgs" | "costs" | "plans" | "logs">("orgs");
  const [searchQuery, setSearchQuery] = useState("");

  // Modals / active items state
  const [editingOrg, setEditingOrg] = useState<AdminOrgOut | null>(null);
  const [newCeiling, setNewCeiling] = useState<string>("");
  const [selectedOrgForCosts, setSelectedOrgForCosts] = useState<string | null>(null);
  const [editingPlan, setEditingPlan] = useState<PlanOut | null>(null);

  // Queries
  const orgs = useAdminOrgs(true);
  const plans = useAdminPlans(true);
  const costSummary = useAdminCostSummary(activeTab === "costs");
  const auditLogs = useAdminAuditLogs(activeTab === "logs");
  const orgCostDetails = useAdminOrgCosts(selectedOrgForCosts ?? undefined, !!selectedOrgForCosts);

  // Mutations
  const setPlan = useMutation({
    mutationFn: ({ orgId, code }: { orgId: string; code: string }) =>
      api(`/admin/orgs/${orgId}/plan`, { method: "PUT", body: { plan_code: code } }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-orgs"] });
      void qc.invalidateQueries({ queryKey: ["admin-cost-summary"] });
    },
  });

  const toggleArabic = useMutation({
    mutationFn: ({ orgId, on }: { orgId: string; on: boolean }) =>
      api(`/admin/orgs/${orgId}`, { method: "PATCH", body: { addons: { arabic: on } } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin-orgs"] }),
  });

  const updateOrgCeiling = useMutation({
    mutationFn: ({ orgId, ceiling }: { orgId: string; ceiling: number | null }) =>
      api(`/admin/orgs/${orgId}`, {
        method: "PATCH",
        body: { cost_ceiling_override_usd: ceiling },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-orgs"] });
      void qc.invalidateQueries({ queryKey: ["admin-cost-summary"] });
      setEditingOrg(null);
    },
  });

  const resetCounters = useAdminResetCounters();
  const updatePlan = useAdminUpdatePlan();

  if (orgs.isPending || plans.isPending) return <PageLoader />;
  if (orgs.isError) return <ErrorState error={orgs.error} />;

  const filteredOrgs = (orgs.data ?? []).filter(
    (o) =>
      o.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      o.slug.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const getStatusBadge = (o: AdminOrgOut) => {
    if (o.is_trial_expired) {
      return <Badge variant="muted">{t("status.trialExpired")}</Badge>;
    }
    if (o.spend_ratio >= 1.0) {
      return (
        <Badge variant="warning" className="border-rose-300 bg-rose-100 text-rose-800">
          <ShieldAlert className="me-1 h-3 w-3" />
          {t("status.paused")}
        </Badge>
      );
    }
    if (o.spend_ratio >= 0.8) {
      return (
        <Badge variant="warning">
          <AlertTriangle className="me-1 h-3 w-3" />
          {t("status.warning")}
        </Badge>
      );
    }
    return (
      <Badge variant="success">
        <CheckCircle2 className="me-1 h-3 w-3" />
        {t("status.normal")}
      </Badge>
    );
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6">
      <PageHeader title={t("title")} description={t("description")} />

      {/* Tabs */}
      <div className="border-border flex flex-wrap gap-2 border-b pb-3">
        {(["orgs", "costs", "plans", "logs"] as const).map((tab) => (
          <Button
            key={tab}
            variant={activeTab === tab ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveTab(tab)}
          >
            {tab === "orgs" && <Building2 className="me-1.5 h-4 w-4" />}
            {tab === "costs" && <DollarSign className="me-1.5 h-4 w-4" />}
            {tab === "plans" && <Layers className="me-1.5 h-4 w-4" />}
            {tab === "logs" && <Cpu className="me-1.5 h-4 w-4" />}
            {t(`tabs.${tab}`)}
          </Button>
        ))}
      </div>

      {(setPlan.isError || toggleArabic.isError || updateOrgCeiling.isError) && (
        <Alert tone="error">
          {errorMessage(setPlan.error ?? toggleArabic.error ?? updateOrgCeiling.error, tc)}
        </Alert>
      )}

      {/* TAB 1: Organizations & Plans */}
      {activeTab === "orgs" && (
        <div className="space-y-4">
          <div className="flex flex-col items-stretch justify-between gap-3 sm:flex-row sm:items-center">
            <div className="relative max-w-md flex-1">
              <Search className="text-muted-foreground absolute start-3 top-2.5 h-4 w-4" />
              <Input
                placeholder={t("actions.searchOrgs")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="ps-9 text-xs"
              />
            </div>
            <div className="text-muted-foreground text-xs">
              {filteredOrgs.length} {t("columns.org")}
            </div>
          </div>

          <Card className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 border-b text-start text-xs">
                <tr>
                  <th className="px-4 py-3 text-start font-medium">{t("columns.org")}</th>
                  <th className="px-4 py-3 text-start font-medium">{t("columns.plan")}</th>
                  <th className="px-4 py-3 text-start font-medium">{t("columns.arabic")}</th>
                  <th className="px-4 py-3 text-start font-medium">{t("columns.spend")}</th>
                  <th className="px-4 py-3 text-start font-medium">{t("columns.status")}</th>
                  <th className="px-4 py-3 text-start font-medium">{t("columns.members")}</th>
                  <th className="px-4 py-3 text-start font-medium">{t("columns.sites")}</th>
                  <th className="px-4 py-3 text-start font-medium">{t("columns.created")}</th>
                  <th className="px-4 py-3 text-end font-medium">{t("columns.actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y text-xs">
                {filteredOrgs.map((o) => (
                  <tr key={o.id} className="hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-3">
                      <div className="text-foreground font-semibold">{o.name}</div>
                      <div className="text-muted-foreground font-mono text-[11px]">{o.slug}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Select
                        value={o.plan_code}
                        className="h-8 w-32 text-xs"
                        aria-label={t("columns.plan")}
                        onChange={(e) => setPlan.mutate({ orgId: o.id, code: e.target.value })}
                      >
                        {(plans.data ?? []).map((p) => (
                          <option key={p.code} value={p.code}>
                            {p.name}
                          </option>
                        ))}
                      </Select>
                    </td>
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={!!o.addons.arabic}
                        aria-label={t("columns.arabic")}
                        className="border-input text-primary focus:ring-primary size-4 rounded"
                        onChange={(e) => toggleArabic.mutate({ orgId: o.id, on: e.target.checked })}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium">
                        ${Number(o.current_spend_usd ?? 0).toFixed(2)}
                        <span className="text-muted-foreground text-[11px]">
                          {" "}
                          / $
                          {o.effective_ceiling_usd
                            ? Number(o.effective_ceiling_usd).toFixed(2)
                            : "∞"}
                        </span>
                      </div>
                      {o.effective_ceiling_usd && (
                        <div className="bg-muted mt-1 h-1.5 w-24 overflow-hidden rounded-full">
                          <div
                            className={`h-full rounded-full ${
                              o.spend_ratio >= 1.0
                                ? "bg-rose-500"
                                : o.spend_ratio >= 0.8
                                  ? "bg-amber-500"
                                  : "bg-emerald-500"
                            }`}
                            style={{ width: `${Math.min(100, (o.spend_ratio ?? 0) * 100)}%` }}
                          />
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">{getStatusBadge(o)}</td>
                    <td className="px-4 py-3">{o.members}</td>
                    <td className="px-4 py-3">{o.sites}</td>
                    <td className="text-muted-foreground px-4 py-3">{formatDate(o.created_at)}</td>
                    <td className="px-4 py-3 text-end">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2 text-[11px]"
                          onClick={() => {
                            setEditingOrg(o);
                            setNewCeiling(
                              o.cost_ceiling_override_usd
                                ? String(o.cost_ceiling_override_usd)
                                : "",
                            );
                          }}
                        >
                          <Edit className="me-1 h-3 w-3" />
                          {t("actions.editCeiling")}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-[11px]"
                          onClick={() => setSelectedOrgForCosts(o.id)}
                        >
                          {t("actions.viewDetails")}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          {/* Edit Ceiling Modal / Drawer */}
          {editingOrg && (
            <Card className="border-primary/40 bg-muted/10 p-4">
              <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
                <div>
                  <h4 className="text-sm font-semibold">
                    {t("actions.editCeiling")}: {editingOrg.name}
                  </h4>
                  <p className="text-muted-foreground text-xs">
                    Plan default: ${editingOrg.effective_ceiling_usd ?? "None"}. Set a specific
                    override or clear it.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    step="0.01"
                    placeholder={t("actions.customCeilingPlaceholder")}
                    value={newCeiling}
                    onChange={(e) => setNewCeiling(e.target.value)}
                    className="h-8 w-36 text-xs"
                  />
                  <Button
                    size="sm"
                    className="h-8 text-xs"
                    disabled={updateOrgCeiling.isPending}
                    onClick={() => {
                      const val = newCeiling.trim() ? parseFloat(newCeiling.trim()) : null;
                      updateOrgCeiling.mutate({ orgId: editingOrg.id, ceiling: val });
                    }}
                  >
                    {t("actions.save")}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs"
                    onClick={() => setEditingOrg(null)}
                  >
                    {t("actions.cancel")}
                  </Button>
                </div>
              </div>
            </Card>
          )}

          {/* Org Detailed Costs Modal */}
          {selectedOrgForCosts && (
            <Card className="border-border">
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <div>
                  <CardTitle className="text-sm font-semibold">
                    {t("costs.topTenants")}: {orgCostDetails.data?.org_name}
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Current Spend: ${Number(orgCostDetails.data?.current_spend_usd ?? 0).toFixed(4)}{" "}
                    / Ceiling: ${orgCostDetails.data?.effective_ceiling_usd ?? "None"}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    disabled={resetCounters.isPending}
                    onClick={() => {
                      if (window.confirm(t("actions.resetConfirm"))) {
                        resetCounters.mutate(selectedOrgForCosts);
                      }
                    }}
                  >
                    <RotateCcw className="me-1 h-3 w-3" />
                    {t("actions.resetCounters")}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => setSelectedOrgForCosts(null)}
                  >
                    ✕
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {orgCostDetails.isPending ? (
                  <PageLoader />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-muted/50 border-b text-start">
                        <tr>
                          <th className="px-3 py-2 text-start font-medium">Period</th>
                          <th className="px-3 py-2 text-start font-medium">Category</th>
                          <th className="px-3 py-2 text-start font-medium">Provider</th>
                          <th className="px-3 py-2 text-start font-medium">Units</th>
                          <th className="px-3 py-2 text-end font-medium">Cost ($)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {(orgCostDetails.data?.counters ?? []).length === 0 ? (
                          <tr>
                            <td colSpan={5} className="text-muted-foreground py-4 text-center">
                              No usage counters recorded yet for this organization.
                            </td>
                          </tr>
                        ) : (
                          orgCostDetails.data?.counters.map((c, idx) => (
                            <tr key={idx}>
                              <td className="text-muted-foreground px-3 py-2">
                                {c.period_start
                                  ? new Date(String(c.period_start)).toLocaleDateString()
                                  : ""}
                              </td>
                              <td className="px-3 py-2 font-medium capitalize">
                                {String(c.category)}
                              </td>
                              <td className="px-3 py-2 capitalize">{String(c.provider)}</td>
                              <td className="px-3 py-2">{String(c.units)}</td>
                              <td className="px-3 py-2 text-end font-mono">
                                ${Number(c.cost_usd).toFixed(4)}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* TAB 2: API Costs & Providers */}
      {activeTab === "costs" && (
        <div className="space-y-6">
          {costSummary.isPending ? (
            <PageLoader />
          ) : costSummary.isError ? (
            <ErrorState error={costSummary.error} />
          ) : (
            <>
              {/* Stat KPI Cards */}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Card className="p-4">
                  <div className="text-muted-foreground flex items-center justify-between text-xs font-medium">
                    <span>{t("costs.totalSpend")}</span>
                    <DollarSign className="h-4 w-4 text-emerald-600" />
                  </div>
                  <div className="text-foreground mt-2 text-2xl font-bold">
                    ${Number(costSummary.data.total_spend_usd).toFixed(2)}
                  </div>
                  <p className="text-muted-foreground mt-1 text-[11px]">
                    {t("costs.totalSpendDesc")}
                  </p>
                </Card>

                <Card className="p-4">
                  <div className="text-muted-foreground flex items-center justify-between text-xs font-medium">
                    <span>{t("costs.activeTenants")}</span>
                    <Building2 className="h-4 w-4 text-indigo-600" />
                  </div>
                  <div className="text-foreground mt-2 text-2xl font-bold">
                    {costSummary.data.total_orgs}
                  </div>
                  <p className="text-muted-foreground mt-1 text-[11px]">
                    {t("costs.activeTenantsDesc")}
                  </p>
                </Card>

                <Card className="p-4">
                  <div className="text-muted-foreground flex items-center justify-between text-xs font-medium">
                    <span>{t("costs.warningTenants")}</span>
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                  </div>
                  <div className="mt-2 text-2xl font-bold text-amber-600">
                    {costSummary.data.orgs_at_warning}
                  </div>
                  <p className="text-muted-foreground mt-1 text-[11px]">
                    {t("costs.warningTenantsDesc")}
                  </p>
                </Card>

                <Card className="p-4">
                  <div className="text-muted-foreground flex items-center justify-between text-xs font-medium">
                    <span>{t("costs.pausedTenants")}</span>
                    <ShieldAlert className="h-4 w-4 text-rose-600" />
                  </div>
                  <div className="mt-2 text-2xl font-bold text-rose-600">
                    {costSummary.data.orgs_at_paused}
                  </div>
                  <p className="text-muted-foreground mt-1 text-[11px]">
                    {t("costs.pausedTenantsDesc")}
                  </p>
                </Card>
              </div>

              {/* Provider & Category Breakdown */}
              <div className="grid gap-6 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold">
                      {t("costs.providerBreakdown")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {Object.entries(costSummary.data.provider_breakdown).length === 0 ? (
                      <p className="text-muted-foreground py-4 text-center text-xs">
                        No provider usage recorded yet.
                      </p>
                    ) : (
                      Object.entries(costSummary.data.provider_breakdown).map(([prov, amt]) => (
                        <div key={prov} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold capitalize">{prov}</span>
                            <span className="font-mono">${Number(amt).toFixed(4)}</span>
                          </div>
                          <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
                            <div
                              className="bg-primary h-full rounded-full"
                              style={{
                                width: `${
                                  Number(costSummary.data.total_spend_usd) > 0
                                    ? (Number(amt) / Number(costSummary.data.total_spend_usd)) * 100
                                    : 0
                                }%`,
                              }}
                            />
                          </div>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold">
                      {t("costs.categoryBreakdown")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {Object.entries(costSummary.data.category_breakdown).length === 0 ? (
                      <p className="text-muted-foreground py-4 text-center text-xs">
                        No category usage recorded yet.
                      </p>
                    ) : (
                      Object.entries(costSummary.data.category_breakdown).map(([cat, amt]) => (
                        <div key={cat} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold capitalize">
                              {cat.replace("_", " ")}
                            </span>
                            <span className="font-mono">${Number(amt).toFixed(4)}</span>
                          </div>
                          <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
                            <div
                              className="h-full rounded-full bg-indigo-500"
                              style={{
                                width: `${
                                  Number(costSummary.data.total_spend_usd) > 0
                                    ? (Number(amt) / Number(costSummary.data.total_spend_usd)) * 100
                                    : 0
                                }%`,
                              }}
                            />
                          </div>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Top Spenders Table */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">{t("costs.topTenants")}</CardTitle>
                </CardHeader>
                <CardContent className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/50 border-b text-start">
                      <tr>
                        <th className="px-3 py-2 text-start font-medium">{t("columns.org")}</th>
                        <th className="px-3 py-2 text-start font-medium">{t("columns.plan")}</th>
                        <th className="px-3 py-2 text-start font-medium">{t("costs.spend")}</th>
                        <th className="px-3 py-2 text-start font-medium">{t("costs.ceiling")}</th>
                        <th className="px-3 py-2 text-end font-medium">{t("costs.ratio")}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {costSummary.data.top_spending_orgs.map((o) => (
                        <tr key={String(o.org_id)}>
                          <td className="px-3 py-2 font-medium">{String(o.name)}</td>
                          <td className="px-3 py-2 capitalize">{String(o.plan_code)}</td>
                          <td className="px-3 py-2 font-mono">${Number(o.spend_usd).toFixed(2)}</td>
                          <td className="px-3 py-2 font-mono">
                            {o.ceiling_usd ? `$${Number(o.ceiling_usd).toFixed(2)}` : "None"}
                          </td>
                          <td className="px-3 py-2 text-end font-mono">
                            {o.ratio !== undefined
                              ? `${(Number(o.ratio) * 100).toFixed(0)}%`
                              : "0%"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}

      {/* TAB 3: Plan Configurations */}
      {activeTab === "plans" && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold">{t("plans.title")}</CardTitle>
              <CardDescription className="text-xs">{t("plans.desc")}</CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-muted/50 border-b text-start">
                  <tr>
                    <th className="px-3 py-2 text-start font-medium">{t("plans.code")}</th>
                    <th className="px-3 py-2 text-start font-medium">{t("plans.name")}</th>
                    <th className="px-3 py-2 text-start font-medium">{t("plans.maxSites")}</th>
                    <th className="px-3 py-2 text-start font-medium">{t("plans.maxKeywords")}</th>
                    <th className="px-3 py-2 text-start font-medium">{t("plans.maxPrompts")}</th>
                    <th className="px-3 py-2 text-start font-medium">{t("plans.frequency")}</th>
                    <th className="px-3 py-2 text-start font-medium">{t("plans.audits")}</th>
                    <th className="px-3 py-2 text-start font-medium">{t("plans.ceiling")}</th>
                    <th className="px-3 py-2 text-end font-medium">{t("columns.actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(plans.data ?? []).map((p) => (
                    <tr key={p.code}>
                      <td className="px-3 py-2 font-mono font-semibold">{p.code}</td>
                      <td className="px-3 py-2">{p.name}</td>
                      <td className="px-3 py-2">{p.max_sites}</td>
                      <td className="px-3 py-2">{p.max_keywords}</td>
                      <td className="px-3 py-2">{p.max_prompts}</td>
                      <td className="px-3 py-2 capitalize">{p.check_frequency}</td>
                      <td className="px-3 py-2">{p.audits_per_month}</td>
                      <td className="px-3 py-2 font-mono">
                        $
                        {(p as unknown as { monthly_cost_ceiling_usd?: number })
                          .monthly_cost_ceiling_usd ?? "5.00"}
                      </td>
                      <td className="px-3 py-2 text-end">
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2 text-[11px]"
                          onClick={() => setEditingPlan(p)}
                        >
                          <Edit className="me-1 h-3 w-3" />
                          {t("actions.editPlan")}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Edit Plan Modal */}
          {editingPlan && (
            <Card className="border-primary/40 bg-muted/10 p-4">
              <h4 className="mb-3 text-sm font-semibold">
                {t("actions.editPlan")}: {editingPlan.name} ({editingPlan.code})
              </h4>
              <div className="grid gap-3 text-xs sm:grid-cols-3">
                <div>
                  <label className="text-muted-foreground font-medium">{t("plans.maxSites")}</label>
                  <Input
                    type="number"
                    defaultValue={editingPlan.max_sites}
                    id="edit-plan-sites"
                    className="mt-1 h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="text-muted-foreground font-medium">
                    {t("plans.maxKeywords")}
                  </label>
                  <Input
                    type="number"
                    defaultValue={editingPlan.max_keywords}
                    id="edit-plan-keywords"
                    className="mt-1 h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="text-muted-foreground font-medium">
                    {t("plans.maxPrompts")}
                  </label>
                  <Input
                    type="number"
                    defaultValue={editingPlan.max_prompts}
                    id="edit-plan-prompts"
                    className="mt-1 h-8 text-xs"
                  />
                </div>
              </div>
              <div className="mt-4 flex items-center justify-end gap-2">
                <Button
                  size="sm"
                  className="h-8 text-xs"
                  disabled={updatePlan.isPending}
                  onClick={() => {
                    const sitesInput = document.getElementById(
                      "edit-plan-sites",
                    ) as HTMLInputElement;
                    const kwInput = document.getElementById(
                      "edit-plan-keywords",
                    ) as HTMLInputElement;
                    const promptsInput = document.getElementById(
                      "edit-plan-prompts",
                    ) as HTMLInputElement;
                    updatePlan.mutate(
                      {
                        code: editingPlan.code,
                        body: {
                          max_sites: parseInt(sitesInput.value, 10),
                          max_keywords: parseInt(kwInput.value, 10),
                          max_prompts: parseInt(promptsInput.value, 10),
                        },
                      },
                      { onSuccess: () => setEditingPlan(null) },
                    );
                  }}
                >
                  {updatePlan.isPending && <RefreshCw className="me-1 h-3 w-3 animate-spin" />}
                  {t("actions.save")}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 text-xs"
                  onClick={() => setEditingPlan(null)}
                >
                  {t("actions.cancel")}
                </Button>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* TAB 4: Platform Audit Logs */}
      {activeTab === "logs" && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold">{t("logs.title")}</CardTitle>
              <CardDescription className="text-xs">{t("logs.desc")}</CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              {auditLogs.isPending ? (
                <PageLoader />
              ) : auditLogs.isError ? (
                <ErrorState error={auditLogs.error} />
              ) : (
                <table className="w-full text-xs">
                  <thead className="bg-muted/50 border-b text-start">
                    <tr>
                      <th className="px-3 py-2 text-start font-medium">{t("logs.time")}</th>
                      <th className="px-3 py-2 text-start font-medium">{t("logs.actor")}</th>
                      <th className="px-3 py-2 text-start font-medium">{t("logs.action")}</th>
                      <th className="px-3 py-2 text-start font-medium">{t("logs.target")}</th>
                      <th className="px-3 py-2 text-start font-medium">{t("logs.details")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y font-mono">
                    {(auditLogs.data ?? []).length === 0 ? (
                      <tr>
                        <td
                          colSpan={5}
                          className="text-muted-foreground py-4 text-center font-sans"
                        >
                          No audit entries recorded yet.
                        </td>
                      </tr>
                    ) : (
                      auditLogs.data?.map((entry) => (
                        <tr key={entry.id}>
                          <td className="text-muted-foreground px-3 py-2">
                            {new Date(entry.created_at).toLocaleString()}
                          </td>
                          <td className="text-foreground px-3 py-2 font-sans">
                            {entry.actor_email ?? String(entry.actor_user_id ?? "system")}
                          </td>
                          <td className="text-primary px-3 py-2 font-semibold">{entry.action}</td>
                          <td className="text-muted-foreground px-3 py-2">
                            {entry.target_type ? `${entry.target_type}:${entry.target_id}` : "-"}
                          </td>
                          <td className="text-muted-foreground max-w-xs truncate px-3 py-2">
                            {JSON.stringify(entry.data)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
