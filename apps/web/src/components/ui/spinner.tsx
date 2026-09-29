import { Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("size-5 animate-spin", className)} aria-hidden />;
}

export function PageLoader() {
  const { t } = useTranslation();
  return (
    <div
      className="text-muted-foreground flex min-h-[40vh] items-center justify-center gap-3"
      role="status"
    >
      <Spinner />
      <span>{t("loading")}</span>
    </div>
  );
}
