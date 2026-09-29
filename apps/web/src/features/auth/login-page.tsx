import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { SessionOut } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { applyLanguage } from "@/lib/i18n";
import { safeNext } from "@/lib/navigation";
import { useSession } from "@/stores/session";
import { AuthCard } from "./auth-card";
import { GoogleButton, OrDivider } from "./google-button";
import { loginSchema, type LoginValues } from "./schemas";

export function LoginPage() {
  const { t } = useTranslation("auth");
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setSession = useSession((s) => s.setSession);
  const [error, setError] = useState<string | null>(
    params.get("error") === "google"
      ? t("googleFailed")
      : params.get("error") === "google_unavailable"
        ? t("googleUnavailable")
        : null,
  );
  const form = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });
  const { errors, isSubmitting } = form.formState;

  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);
    try {
      const session = await api<SessionOut>("/auth/login", { method: "POST", body: values });
      setSession(session);
      await applyLanguage(session.user.ui_language);
      navigate(safeNext(params.get("next")), { replace: true });
    } catch (e) {
      setError(errorMessage(e, t));
    }
  });

  return (
    <AuthCard
      title={t("login.title")}
      description={t("login.description")}
      footer={
        <>
          {t("login.noAccount")}{" "}
          <Link className="text-primary hover:underline" to="/signup">
            {t("login.signupLink")}
          </Link>
        </>
      }
    >
      {error && <Alert tone="error">{error}</Alert>}
      <GoogleButton next={safeNext(params.get("next"))} />
      <OrDivider />
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label={t("fields.email")} error={errors.email && t(errors.email.message!)}>
          <Input type="email" autoComplete="email" {...form.register("email")} />
        </Field>
        <Field label={t("fields.password")} error={errors.password && t(errors.password.message!)}>
          <Input type="password" autoComplete="current-password" {...form.register("password")} />
        </Field>
        <div className="flex justify-end">
          <Link to="/forgot-password" className="text-primary text-sm hover:underline">
            {t("login.forgot")}
          </Link>
        </div>
        <Button type="submit" className="w-full" loading={isSubmitting}>
          {t("login.submit")}
        </Button>
      </form>
    </AuthCard>
  );
}
