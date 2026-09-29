import { API_URL } from "./config";
import { useSession } from "@/stores/session";
import type { SessionOut } from "./api-types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public detail: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

type Options = { method?: string; body?: unknown; signal?: AbortSignal; skipRefresh?: boolean };

let refreshing: Promise<boolean> | null = null;

/** Single-flight refresh: concurrent 401s share one /auth/refresh call. */
export function refreshSession(): Promise<boolean> {
  refreshing ??= (async () => {
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) return false;
      useSession.getState().setSession((await res.json()) as SessionOut);
      return true;
    } catch {
      return false;
    } finally {
      setTimeout(() => (refreshing = null), 0);
    }
  })();
  return refreshing;
}

async function toError(res: Response): Promise<ApiError> {
  let detail: Record<string, unknown> = {};
  try {
    const data = await res.json();
    detail =
      typeof data?.detail === "object" && data.detail ? data.detail : { message: data?.detail };
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(
    res.status,
    String(detail.code ?? "http_error"),
    String(detail.message ?? res.statusText),
    detail,
  );
}

export async function api<T>(path: string, opts: Options = {}): Promise<T> {
  const { csrfToken, currentOrgId } = useSession.getState();
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
  if (currentOrgId) headers["X-Org-Id"] = currentOrgId;

  const res = await fetch(`${API_URL}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    credentials: "include",
    signal: opts.signal,
  });

  if (res.status === 401 && !opts.skipRefresh && !path.startsWith("/auth/")) {
    if (await refreshSession()) return api<T>(path, { ...opts, skipRefresh: true });
    useSession.getState().clear();
  }
  if (!res.ok) throw await toError(res);
  return (await res.json()) as T;
}
