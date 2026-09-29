import { useId, type ReactElement, cloneElement } from "react";
import { cn } from "@/lib/utils";

type FieldProps = {
  label: React.ReactNode;
  hint?: React.ReactNode;
  error?: string;
  className?: string;
  children: ReactElement<{ id?: string; "aria-invalid"?: boolean; "aria-describedby"?: string }>;
};

/** Label + control + hint/error, wired for accessibility. */
export function Field({ label, hint, error, className, children }: FieldProps) {
  const id = useId();
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div className={cn("space-y-1.5", className)}>
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      {cloneElement(children, { id, "aria-invalid": !!error, "aria-describedby": describedBy })}
      {error ? (
        <p id={`${id}-error`} className="text-destructive text-sm">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-muted-foreground text-sm">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
