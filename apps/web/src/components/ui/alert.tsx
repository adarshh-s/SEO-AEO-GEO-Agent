import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

const styles = {
  info: "border-blue-200 bg-blue-50 text-blue-900",
  error: "border-red-200 bg-red-50 text-red-900",
  success: "border-green-200 bg-green-50 text-green-900",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
};
const icons = { info: Info, error: AlertCircle, success: CheckCircle2, warning: AlertCircle };

export function Alert({
  tone = "info",
  children,
  className,
}: {
  tone?: keyof typeof styles;
  children: ReactNode;
  className?: string;
}) {
  const Icon = icons[tone];
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cn("flex gap-3 rounded-md border p-3 text-sm", styles[tone], className)}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div className="space-y-1">{children}</div>
    </div>
  );
}
