import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import type { SessionOut } from "@/lib/api-types";
import { errorMessage } from "@/lib/errors";
import { useSession } from "@/stores/session";
import { AuthCard } from "./auth-card";
import { forgotSchema, resetSchema } from "./schemas";

export function ForgotPasswordPage() {
  const { t } = useTranslation("auth");
  const [sent, setSent] = useState(false);
  const form = useForm<{ email: string }>({ resolver: zodResolver(forgotSchema) });
  const { errors, isSubmitting } = form.formState;
  const onSubmit = form.handleSubmit(async (values) => {
    await api("/auth/password-reset/request", { method: "POST", body: values }).catch(
      () => undefined,
    );
    setSent(true);
  });
  return (
    <AuthCard
      title={t("forgot.title")}
      description={t("forgot.description")}
      footer={
        <Link to="/login" className="text-primary hover:underline">
          {t("backToLogin")}
        </Link>
      }
    >
      {sent ? (
        <Alert tone="success">{t("forgot.sent")}</Alert>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <Field label={t("fields.email")} error={errors.email && t(errors.email.message!)}>
            <Input type="email" autoComplete="email" {...form.register("email")} />
          </Field>
          <Button type="submit" className="w-full" loading={isSubmitting}>
            {t("forgot.submit")}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}

export function ResetPasswordPage() {
  const { t } = useTranslation("auth");
  const [params] = useSearchParams();
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<{ password: string; confirm: string }>({
    resolver: zodResolver(resetSchema),
  });
  const { errors, isSubmitting } = form.formState;
  const onSubmit = form.handleSubmit(async ({ password }) => {
    setError(null);
    try {
      await api("/auth/password-reset", {
        method: "POST",
        body: { token: params.get("token") ?? "", password },
      });
      setDone(true);
    } catch (e) {
      setError(errorMessage(e, t));
    }
  });
  return (
    <AuthCard
      title={t("reset.title")}
      footer={
        <Link to="/login" className="text-primary hover:underline">
          {t("backToLogin")}
        </Link>
      }
    >
      {error && <Alert tone="error">{error}</Alert>}
      {done ? (
        <Alert tone="success">{t("reset.done")}</Alert>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <Field
            label={t("fields.newPassword")}
            error={errors.password && t(errors.password.message!)}
          >
            <Input type="password" autoComplete="new-password" {...form.register("password")} />
          </Field>
          <Field
            label={t("fields.confirmPassword")}
            error={errors.confirm && t(errors.confirm.message!)}
          >
            <Input type="password" autoComplete="new-password" {...form.register("confirm")} />
          </Field>
          <Button type="submit" className="w-full" loading={isSubmitting}>
            {t("reset.submit")}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}

/** Runs a token mutation once on mount (verify email / accept invite). */
function useTokenAction<T>(fn: (token: string) => Promise<T>) {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const mutation = useMutation({ mutationFn: fn });
  const started = useRef(false);
  useEffect(() => {
    if (!started.current) {
      started.current = true;
      mutation.mutate(token);
    }
  }, [mutation, token]);
  return mutation;
}

export function VerifyEmailPage() {
  const { t } = useTranslation("auth");
  const signedIn = useSession((s) => !!s.user);
  const m = useTokenAction((token) =>
    api("/auth/verify-email", { method: "POST", body: { token } }),
  );
  return (
    <AuthCard title={t("verify.title")}>
      {m.isPending && <Spinner />}
      {m.isSuccess && <Alert tone="success">{t("verify.done")}</Alert>}
      {m.isError && <Alert tone="error">{errorMessage(m.error, t)}</Alert>}
      <Button asChild variant="outline" className="w-full">
        <Link to={signedIn ? "/app" : "/login"}>{t("continue")}</Link>
      </Button>
    </AuthCard>
  );
}

export function AcceptInvitePage() {
  const { t } = useTranslation("auth");
  const navigate = useNavigate();
  const { setSession, switchOrg } = useSession();
  const m = useTokenAction(async (token) => {
    const before = new Set(useSession.getState().orgs.map((o) => o.id));
    const session = await api<SessionOut>("/invitations/accept", {
      method: "POST",
      body: { token },
    });
    setSession(session);
    const joined = session.orgs.find((o) => !before.has(o.id));
    if (joined) switchOrg(joined.id);
    navigate("/app", { replace: true });
    return session;
  });
  return (
    <AuthCard title={t("invite.title")}>
      {m.isPending && <Spinner />}
      {m.isError && <Alert tone="error">{errorMessage(m.error, t)}</Alert>}
    </AuthCard>
  );
}
