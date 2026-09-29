import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { SessionOut } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { useSession } from "@/stores/session";
import { AuthCard } from "./auth-card";
import { GoogleButton, OrDivider } from "./google-button";
import { signupSchema, type SignupValues } from "./schemas";

export function SignupPage() {
  const { t, i18n } = useTranslation("auth");
  const navigate = useNavigate();
  const setSession = useSession((s) => s.setSession);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<SignupValues>({ resolver: zodResolver(signupSchema) });
  const { errors, isSubmitting } = form.formState;

  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);
    try {
      const session = await api<SessionOut>("/auth/signup", {
        method: "POST",
        body: { ...values, org_name: values.org_name || undefined, ui_language: i18n.language },
      });
      setSession(session);
      navigate("/app/onboarding", { replace: true });
    } catch (e) {
      setError(errorMessage(e, t));
    }
  });

  return (
    <AuthCard
      title={t("signup.title")}
      description={t("signup.description")}
      footer={
        <>
          {t("signup.haveAccount")}{" "}
          <Link className="text-primary hover:underline" to="/login">
            {t("signup.loginLink")}
          </Link>
        </>
      }
    >
      {error && <Alert tone="error">{error}</Alert>}
      <GoogleButton next="/app/onboarding" />
      <OrDivider />
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field
          label={t("fields.fullName")}
          error={errors.full_name && t(errors.full_name.message!)}
        >
          <Input autoComplete="name" {...form.register("full_name")} />
        </Field>
        <Field label={t("fields.orgName")} hint={t("signup.orgHint")}>
          <Input autoComplete="organization" {...form.register("org_name")} />
        </Field>
        <Field label={t("fields.email")} error={errors.email && t(errors.email.message!)}>
          <Input type="email" autoComplete="email" {...form.register("email")} />
        </Field>
        <Field
          label={t("fields.password")}
          hint={t("signup.passwordHint")}
          error={errors.password && t(errors.password.message!)}
        >
          <Input type="password" autoComplete="new-password" {...form.register("password")} />
        </Field>
        <Button type="submit" className="w-full" loading={isSubmitting}>
          {t("signup.submit")}
        </Button>
        <p className="text-muted-foreground text-xs">
          {t("signup.legal.before")}{" "}
          <Link to="/terms" className="underline">
            {t("signup.legal.terms")}
          </Link>{" "}
          {t("signup.legal.and")}{" "}
          <Link to="/privacy" className="underline">
            {t("signup.legal.privacy")}
          </Link>
          .
        </p>
      </form>
    </AuthCard>
  );
}
