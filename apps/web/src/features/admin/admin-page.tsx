import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Alert } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { PageLoader } from "@/components/ui/spinner";
import { ErrorState, PageHeader } from "@/components/ui/states";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/i18n";
import { useAdminOrgs, useAdminPlans } from "@/lib/queries";

/** Minimal platform admin (manual plan assignment, D20). The full admin panel is Phase 6. */
export function AdminPage() {
  const { t } = useTranslation("admin");
  const tc = useTranslation().t;
  const orgs = useAdminOrgs(true);
  const plans = useAdminPlans(true);
  const qc = useQueryClient();
  const setPlan = useMutation({
    mutationFn: ({ orgId, code }: { orgId: string; code: string }) =>
      api(`/admin/orgs/${orgId}/plan`, { method: "PUT", body: { plan_code: code } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin-orgs"] }),
  });
  const toggleArabic = useMutation({
    mutationFn: ({ orgId, on }: { orgId: string; on: boolean }) =>
      api(`/admin/orgs/${orgId}`, { method: "PATCH", body: { addons: { arabic: on } } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin-orgs"] }),
  });
  if (orgs.isPending || plans.isPending) return <PageLoader />;
  if (orgs.isError) return <ErrorState error={orgs.error} />;
  return (
    <>
      <PageHeader title={t("title")} description={t("description")} />
      {(setPlan.isError || toggleArabic.isError) && (
        <Alert tone="error" className="mb-4">
          {errorMessage(setPlan.error ?? toggleArabic.error, tc)}
        </Alert>
      )}
      <Card className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 border-b text-start">
            <tr>
              {["org", "plan", "arabic", "members", "sites", "created"].map((h) => (
                <th key={h} className="px-4 py-2 text-start font-medium">
                  {t(`columns.${h}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {orgs.data.map((o) => (
              <tr key={o.id}>
                <td className="px-4 py-2">
                  <div className="font-medium">{o.name}</div>
                  <div className="text-muted-foreground text-xs">{o.slug}</div>
                </td>
                <td className="px-4 py-2">
                  <Select
                    value={o.plan_code}
                    className="w-36"
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
                <td className="px-4 py-2">
                  <input
                    type="checkbox"
                    checked={!!o.addons.arabic}
                    aria-label={t("columns.arabic")}
                    onChange={(e) => toggleArabic.mutate({ orgId: o.id, on: e.target.checked })}
                  />
                </td>
                <td className="px-4 py-2">{o.members}</td>
                <td className="px-4 py-2">{o.sites}</td>
                <td className="text-muted-foreground px-4 py-2">{formatDate(o.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
