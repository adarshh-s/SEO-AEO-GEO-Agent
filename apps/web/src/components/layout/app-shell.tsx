import { useQueryClient } from "@tanstack/react-query";
import {
  BarChart3,
  Bot,
  FileSearch,
  FileText,
  Globe,
  LayoutDashboard,
  LogOut,
  Menu,
  Plug,
  Settings,
  Shield,
  Wrench,
  X,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet, useNavigate } from "react-router";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { PRODUCT_NAME } from "@/lib/brand";
import { cn } from "@/lib/utils";
import { useSession } from "@/stores/session";
import { LanguageToggle } from "./language-toggle";
import { Logo } from "./logo";

type NavItem = { to: string; key: string; icon: LucideIcon; end?: boolean };

const NAV: NavItem[] = [
  { to: "/app", key: "overview", icon: LayoutDashboard, end: true },
  { to: "/app/keywords", key: "keywords", icon: BarChart3 },
  { to: "/app/ai-visibility", key: "aiVisibility", icon: Bot },
  { to: "/app/fixes", key: "fixes", icon: Wrench },
  { to: "/app/audits", key: "audits", icon: FileSearch },
  { to: "/app/reports", key: "reports", icon: FileText },
  { to: "/app/sites", key: "sites", icon: Globe },
  { to: "/app/integrations", key: "integrations", icon: Plug },
  { to: "/app/settings", key: "settings", icon: Settings },
];

function OrgSwitcher() {
  const { t } = useTranslation();
  const { orgs, currentOrgId, switchOrg } = useSession();
  const qc = useQueryClient();
  if (orgs.length < 2) {
    return <span className="truncate text-sm font-medium">{orgs[0]?.name}</span>;
  }
  return (
    <label className="min-w-0">
      <span className="sr-only">{t("nav.organization")}</span>
      <select
        className="bg-background max-w-48 truncate rounded-md border px-2 py-1 text-sm"
        value={currentOrgId ?? ""}
        onChange={(e) => {
          switchOrg(e.target.value);
          qc.clear();
        }}
      >
        {orgs.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation();
  const isAdmin = useSession((s) => s.user?.is_platform_admin);
  const items = isAdmin ? [...NAV, { to: "/app/admin", key: "admin", icon: Shield }] : NAV;
  return (
    <nav className="space-y-1 p-3" aria-label={t("nav.main")}>
      {items.map(({ to, key, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )
          }
        >
          <Icon className="size-4" aria-hidden />
          {t(`nav.${key}`)}
        </NavLink>
      ))}
    </nav>
  );
}

export function AppShell() {
  const { t } = useTranslation();
  const user = useSession((s) => s.user);
  const clear = useSession((s) => s.clear);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);

  async function signOut() {
    try {
      await api("/auth/logout", { method: "POST" });
    } finally {
      clear();
      qc.clear();
      navigate("/login");
    }
  }

  return (
    <div className="flex min-h-screen">
      <aside className="bg-background hidden w-60 shrink-0 border-e md:block">
        <Link to="/app" className="flex h-16 items-center gap-2 border-b px-5 font-semibold">
          <Logo />
          {PRODUCT_NAME}
        </Link>
        <SidebarNav />
      </aside>

      {open && (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true">
          <button
            className="absolute inset-0 bg-black/40"
            aria-label={t("close")}
            onClick={() => setOpen(false)}
          />
          <div className="bg-background absolute inset-y-0 start-0 w-64 shadow-xl">
            <div className="flex h-16 items-center justify-between border-b px-4">
              <span className="flex items-center gap-2 font-semibold">
                <Logo />
                {PRODUCT_NAME}
              </span>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setOpen(false)}
                aria-label={t("close")}
              >
                <X className="size-5" />
              </Button>
            </div>
            <SidebarNav onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="bg-background flex h-16 items-center gap-3 border-b px-4">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setOpen(true)}
            aria-label={t("nav.openMenu")}
          >
            <Menu className="size-5" />
          </Button>
          <OrgSwitcher />
          <div className="ms-auto flex items-center gap-2">
            <LanguageToggle />
            <span className="text-muted-foreground hidden text-sm sm:inline">
              {user?.full_name}
            </span>
            <Button variant="ghost" size="sm" onClick={() => void signOut()}>
              <LogOut className="rtl-flip size-4" aria-hidden />
              <span className="hidden sm:inline">{t("nav.signOut")}</span>
            </Button>
          </div>
        </header>
        <main className="flex-1 p-4 md:p-8">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
