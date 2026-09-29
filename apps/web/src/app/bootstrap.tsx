import { useEffect, useState, type ReactNode } from "react";
import { api, ApiError, refreshSession } from "@/lib/api";
import type { SessionOut } from "@/lib/api-types";
import { applyLanguage, storedLanguage } from "@/lib/i18n";
import { useSession } from "@/stores/session";
import { PageLoader } from "@/components/ui/spinner";

/** Restore the session (if any) and apply the UI language before rendering. */
export function SessionBootstrap({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const setSession = useSession((s) => s.setSession);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      let lang = storedLanguage();
      try {
        const session = await api<SessionOut>("/auth/me");
        setSession(session);
        lang = session.user.ui_language;
      } catch (e) {
        if (e instanceof ApiError && e.status === 401 && (await refreshSession())) {
          lang = useSession.getState().user?.ui_language ?? lang;
        }
      }
      await applyLanguage(lang);
      if (!cancelled) setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [setSession]);

  return ready ? <>{children}</> : <PageLoader />;
}
