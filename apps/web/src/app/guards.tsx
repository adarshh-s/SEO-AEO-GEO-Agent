import { Navigate, Outlet, useLocation } from "react-router";
import { useSession } from "@/stores/session";

export function RequireAuth() {
  const user = useSession((s) => s.user);
  const location = useLocation();
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return <Outlet />;
}

export function RedirectIfAuthed() {
  const user = useSession((s) => s.user);
  return user ? <Navigate to="/app" replace /> : <Outlet />;
}

export function RequirePlatformAdmin() {
  const isAdmin = useSession((s) => s.user?.is_platform_admin);
  return isAdmin ? <Outlet /> : <Navigate to="/app" replace />;
}
