import { FileSearch, FileText } from "lucide-react";
import { createBrowserRouter, Navigate } from "react-router";
import { AppShell } from "@/components/layout/app-shell";
import { PublicLayout } from "@/components/layout/public-layout";
import { AdminPage } from "@/features/admin/admin-page";
import { OverviewPage } from "@/features/app/overview-page";
import { PlaceholderPage } from "@/features/app/placeholder-page";
import { LoginPage } from "@/features/auth/login-page";
import { SignupPage } from "@/features/auth/signup-page";
import {
  AcceptInvitePage,
  ForgotPasswordPage,
  ResetPasswordPage,
  VerifyEmailPage,
} from "@/features/auth/token-pages";
import { OnboardingPage } from "@/features/onboarding/onboarding-page";
import {
  IntegrationsPage,
  LandingPage,
  LegalPage,
  PricingPage,
} from "@/features/public/public-pages";
import { SettingsPage } from "@/features/settings/settings-page";
import { SiteDetailPage } from "@/features/sites/site-detail-page";
import { SitesPage } from "@/features/sites/sites-page";
import { KeywordsPage } from "@/features/keywords/keywords-page";
import { AiVisibilityPage } from "@/features/ai-visibility/ai-visibility-page";
import { FixesPage } from "@/features/fixes/fixes-page";
import { IntegrationsPage as AppIntegrationsPage } from "@/features/integrations/integrations-page";
import { RedirectIfAuthed, RequireAuth, RequirePlatformAdmin } from "./guards";

export const routes = [
  {
    element: <PublicLayout />,
    children: [
      { path: "/", element: <LandingPage /> },
      { path: "/pricing", element: <PricingPage /> },
      { path: "/integrations", element: <IntegrationsPage /> },
      { path: "/privacy", element: <LegalPage doc="privacy" /> },
      { path: "/terms", element: <LegalPage doc="terms" /> },
      { path: "/verify-email", element: <VerifyEmailPage /> },
      { path: "/reset-password", element: <ResetPasswordPage /> },
      {
        element: <RedirectIfAuthed />,
        children: [
          { path: "/login", element: <LoginPage /> },
          { path: "/signup", element: <SignupPage /> },
          { path: "/forgot-password", element: <ForgotPasswordPage /> },
        ],
      },
      {
        element: <RequireAuth />,
        children: [{ path: "/accept-invite", element: <AcceptInvitePage /> }],
      },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        path: "/app",
        element: <AppShell />,
        children: [
          { index: true, element: <OverviewPage /> },
          { path: "onboarding", element: <OnboardingPage /> },
          { path: "keywords", element: <KeywordsPage /> },
          { path: "ai-visibility", element: <AiVisibilityPage /> },
          { path: "fixes", element: <FixesPage /> },
          { path: "audits", element: <PlaceholderPage section="audits" icon={FileSearch} /> },
          { path: "reports", element: <PlaceholderPage section="reports" icon={FileText} /> },
          { path: "integrations", element: <AppIntegrationsPage /> },
          { path: "sites", element: <SitesPage /> },
          { path: "sites/:siteId", element: <SiteDetailPage /> },
          { path: "settings", element: <SettingsPage /> },
          {
            element: <RequirePlatformAdmin />,
            children: [{ path: "admin", element: <AdminPage /> }],
          },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
];

export const router = createBrowserRouter(routes);
