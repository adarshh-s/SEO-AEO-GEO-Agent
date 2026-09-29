import { create } from "zustand";
import type { OrgSummary, UserOut } from "@/lib/api-types";

const ORG_KEY = "app.currentOrgId";

type SessionState = {
  user: UserOut | null;
  orgs: OrgSummary[];
  currentOrgId: string | null;
  csrfToken: string | null;
  setSession: (s: { user: UserOut; orgs: OrgSummary[]; csrf_token: string }) => void;
  setUser: (user: UserOut) => void;
  setOrgs: (orgs: OrgSummary[]) => void;
  setCsrf: (token: string) => void;
  switchOrg: (orgId: string) => void;
  clear: () => void;
};

function pickOrg(orgs: OrgSummary[], preferred: string | null): string | null {
  if (preferred && orgs.some((o) => o.id === preferred)) return preferred;
  return orgs[0]?.id ?? null;
}

function readStoredOrg(): string | null {
  try {
    return localStorage.getItem(ORG_KEY);
  } catch {
    return null;
  }
}

export const useSession = create<SessionState>((set, get) => ({
  user: null,
  orgs: [],
  currentOrgId: null,
  csrfToken: null,
  setSession: ({ user, orgs, csrf_token }) =>
    set({
      user,
      orgs,
      csrfToken: csrf_token || get().csrfToken,
      currentOrgId: pickOrg(orgs, get().currentOrgId ?? readStoredOrg()),
    }),
  setUser: (user) => set({ user }),
  setOrgs: (orgs) => set({ orgs, currentOrgId: pickOrg(orgs, get().currentOrgId) }),
  setCsrf: (csrfToken) => set({ csrfToken }),
  switchOrg: (orgId) => {
    try {
      localStorage.setItem(ORG_KEY, orgId);
    } catch {
      /* storage unavailable */
    }
    set({ currentOrgId: orgId });
  },
  clear: () => set({ user: null, orgs: [], csrfToken: null }),
}));

export function currentRole(): string | undefined {
  const { orgs, currentOrgId } = useSession.getState();
  return orgs.find((o) => o.id === currentOrgId)?.role;
}

export function useCurrentRole(): string | undefined {
  return useSession((s) => s.orgs.find((o) => o.id === s.currentOrgId)?.role);
}
