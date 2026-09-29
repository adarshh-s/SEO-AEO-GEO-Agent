import { Link, Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { PRODUCT_NAME } from "@/lib/brand";
import { useSession } from "@/stores/session";
import { LanguageToggle } from "./language-toggle";
import { Logo } from "./logo";

export function PublicLayout() {
  const { t } = useTranslation("public");
  const signedIn = useSession((s) => !!s.user);
  return (
    <div className="bg-background flex min-h-screen flex-col">
      <header className="border-b">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <Logo />
            {PRODUCT_NAME}
          </Link>
          <nav className="text-muted-foreground hidden gap-5 text-sm sm:flex">
            <Link to="/pricing" className="hover:text-foreground">
              {t("nav.pricing")}
            </Link>
            <Link to="/integrations" className="hover:text-foreground">
              {t("nav.integrations")}
            </Link>
          </nav>
          <div className="ms-auto flex items-center gap-2">
            <LanguageToggle />
            {signedIn ? (
              <Button asChild size="sm">
                <Link to="/app">{t("nav.openApp")}</Link>
              </Button>
            ) : (
              <>
                <Button asChild variant="ghost" size="sm">
                  <Link to="/login">{t("nav.login")}</Link>
                </Button>
                <Button asChild size="sm">
                  <Link to="/signup">{t("nav.signup")}</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="text-muted-foreground border-t py-8 text-sm">
        <div className="mx-auto flex max-w-6xl flex-wrap gap-6 px-4">
          <span>
            © {new Date().getFullYear()} {PRODUCT_NAME}
          </span>
          <Link to="/privacy" className="hover:text-foreground">
            {t("nav.privacy")}
          </Link>
          <Link to="/terms" className="hover:text-foreground">
            {t("nav.terms")}
          </Link>
        </div>
      </footer>
    </div>
  );
}
