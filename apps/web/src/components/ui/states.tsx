import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Alert } from "./alert";
import { Button } from "./button";
import { errorMessage } from "@/lib/errors";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="bg-background flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed px-6 py-14 text-center">
      <div className="bg-accent text-primary rounded-full p-3">
        <Icon className="size-6" aria-hidden />
      </div>
      <h3 className="text-base font-semibold">{title}</h3>
      {description && <p className="text-muted-foreground max-w-md text-sm">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <Alert tone="error">
      <p>{errorMessage(error, t)}</p>
      {onRetry && (
        <Button size="sm" variant="outline" onClick={onRetry}>
          {t("retry")}
        </Button>
      )}
    </Alert>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-muted-foreground mt-1 text-sm">{description}</p>}
      </div>
      {actions}
    </div>
  );
}
