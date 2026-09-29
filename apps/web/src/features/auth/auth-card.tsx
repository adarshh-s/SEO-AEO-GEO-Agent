import type { ReactNode } from "react";
import { Link } from "react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Logo } from "@/components/layout/logo";

export function AuthCard({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center px-4 py-10">
      <div className="w-full max-w-md space-y-4">
        <Link to="/" className="mx-auto flex w-fit" aria-hidden tabIndex={-1}>
          <Logo className="size-10" />
        </Link>
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">{title}</CardTitle>
            {description && <CardDescription>{description}</CardDescription>}
          </CardHeader>
          <CardContent className="space-y-4">{children}</CardContent>
        </Card>
        {footer && <div className="text-muted-foreground text-center text-sm">{footer}</div>}
      </div>
    </div>
  );
}
