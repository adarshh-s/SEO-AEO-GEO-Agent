import { ArrowRight, Bot, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { DiagnosisOut } from "@/lib/api-types";
import { useDiagnoses, useTriggerDiagnosis } from "@/lib/queries";

interface DiagnosisModalProps {
  siteId: string;
  targetType: "keyword" | "prompt";
  targetId: string;
  targetText: string;
  isOpen: boolean;
  onClose: () => void;
}

export function DiagnosisModal({
  siteId,
  targetType,
  targetId,
  targetText,
  isOpen,
  onClose,
}: DiagnosisModalProps) {
  const { t, i18n } = useTranslation("app");
  const isAr = i18n.language === "ar";

  const triggerDiagnosis = useTriggerDiagnosis(siteId);
  const diagnoses = useDiagnoses(siteId);

  const [triggeredDiagnosis, setTriggeredDiagnosis] = useState<DiagnosisOut | null>(null);

  const matchingDiagnosis =
    diagnoses.data?.find((d) => d.target_type === targetType && d.target_id === targetId) ?? null;

  const activeDiagnosis = triggeredDiagnosis ?? matchingDiagnosis;

  if (!isOpen) return null;

  const handleRunDiagnosis = () => {
    triggerDiagnosis.mutate(
      { target_type: targetType, target_id: targetId },
      {
        onSuccess: (data) => {
          setTriggeredDiagnosis(data);
        },
      },
    );
  };

  const findings = (
    Array.isArray(activeDiagnosis?.findings?.items) ? activeDiagnosis?.findings?.items : []
  ) as Array<{
    code: string;
    severity: string;
    gap_type: string;
    title: Record<string, string> | string;
    explanation: Record<string, string> | string;
  }>;

  const competitors = (activeDiagnosis?.competitor_pages ?? []) as Array<{
    domain: string;
    word_count: number;
    url: string;
  }>;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <Card className="flex max-h-[90vh] w-full max-w-2xl flex-col shadow-2xl">
        <CardHeader className="flex flex-row items-start justify-between border-b pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-indigo-600" />
              <CardTitle className="text-base font-semibold">{t("diagnosis.title")}</CardTitle>
            </div>
            <CardDescription className="text-xs">
              {targetType === "keyword" ? (
                <span className="text-foreground font-semibold">Keyword: {targetText}</span>
              ) : (
                <span className="text-foreground font-semibold">AI Prompt: {targetText}</span>
              )}
            </CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>

        <CardContent className="flex-1 space-y-5 overflow-y-auto p-5">
          {!activeDiagnosis ? (
            <div className="space-y-4 py-8 text-center">
              <Bot className="text-muted-foreground mx-auto h-10 w-10" />
              <p className="text-muted-foreground mx-auto max-w-md text-sm">
                {t("diagnosis.subtitle")}
              </p>
              <Button
                variant="default"
                onClick={handleRunDiagnosis}
                disabled={triggerDiagnosis.isPending}
              >
                <Sparkles className="me-2 h-4 w-4" />
                {triggerDiagnosis.isPending ? t("diagnosis.diagnosing") : t("diagnosis.button")}
              </Button>
            </div>
          ) : (
            <>
              {/* Header stats */}
              <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3">
                <div className="flex items-center gap-2">
                  <Badge variant={activeDiagnosis.status === "completed" ? "success" : "warning"}>
                    {activeDiagnosis.status}
                  </Badge>
                  <span className="text-muted-foreground text-xs">
                    {t("diagnosis.competitorsAnalyzed", { count: competitors.length })}
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRunDiagnosis}
                  disabled={triggerDiagnosis.isPending}
                  className="h-7 text-xs"
                >
                  <Sparkles className="me-1 h-3 w-3" />
                  Re-run Diagnosis
                </Button>
              </div>

              {/* Competitors summary if available */}
              {competitors.length > 0 && (
                <div className="space-y-2">
                  <span className="text-muted-foreground text-xs font-semibold">
                    Top Competitors Analyzed
                  </span>
                  <div className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
                    {competitors.slice(0, 4).map((c, i) => (
                      <div
                        key={i}
                        className="border-border bg-muted/20 flex items-center justify-between truncate rounded-md border p-2"
                      >
                        <span className="text-foreground truncate font-medium">{c.domain}</span>
                        <Badge variant="outline" className="ms-2 shrink-0 text-[10px]">
                          {c.word_count} words
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Identified Gaps / Findings */}
              <div className="space-y-3">
                <span className="text-muted-foreground text-xs font-semibold">
                  {t("diagnosis.detectedGaps")}
                </span>

                {findings.length === 0 ? (
                  <p className="text-muted-foreground py-4 text-center text-xs">
                    {t("diagnosis.noGaps")}
                  </p>
                ) : (
                  <div className="space-y-2.5">
                    {findings.map((f, idx) => {
                      const titleStr =
                        typeof f.title === "object"
                          ? isAr
                            ? f.title.ar || f.title.en
                            : f.title.en
                          : String(f.title);
                      const explStr =
                        typeof f.explanation === "object"
                          ? isAr
                            ? f.explanation.ar || f.explanation.en
                            : f.explanation.en
                          : String(f.explanation);

                      return (
                        <div
                          key={idx}
                          className="border-border bg-card space-y-1.5 rounded-md border p-3.5"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-foreground text-xs font-semibold">
                              {titleStr}
                            </span>
                            <Badge
                              variant={
                                f.severity === "high"
                                  ? "warning"
                                  : f.severity === "medium"
                                    ? "outline"
                                    : "muted"
                              }
                              className="px-1.5 py-0 text-[10px] uppercase"
                            >
                              {f.severity}
                            </Badge>
                          </div>
                          <p className="text-muted-foreground text-xs leading-relaxed">{explStr}</p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </CardContent>

        <div className="bg-muted/20 flex items-center justify-between border-t p-4">
          <Button variant="ghost" size="sm" onClick={onClose} className="text-xs">
            Close
          </Button>

          <Button asChild variant="default" size="sm" className="text-xs">
            <Link to="/app/fixes">
              {t("diagnosis.viewFixes")}
              <ArrowRight className="ms-1.5 h-3.5 w-3.5 rtl:rotate-180" />
            </Link>
          </Button>
        </div>
      </Card>
    </div>
  );
}
