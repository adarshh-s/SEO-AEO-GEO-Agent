import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router";
import { Providers } from "@/app/providers";
import { makeQueryClient } from "@/lib/query-client";

type Handler = (url: string, init: RequestInit) => { status?: number; body: unknown } | undefined;

/** Stub global fetch with a route handler; returns the list of calls for assertions. */
export function mockFetch(handler: Handler) {
  const calls: { url: string; method: string; body: unknown }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init: RequestInit = {}) => {
      const url = String(input);
      const body = init.body ? JSON.parse(String(init.body)) : undefined;
      calls.push({ url, method: init.method ?? "GET", body });
      const res = handler(url, init) ?? {
        status: 404,
        body: { detail: { code: "not_found", message: "nf" } },
      };
      return new Response(JSON.stringify(res.body), {
        status: res.status ?? 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  return calls;
}

export function renderWithProviders(ui: ReactElement, { route = "/" } = {}) {
  const client = makeQueryClient();
  client.setDefaultOptions({ queries: { retry: false } });
  return render(
    <Providers client={client}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </Providers>,
  );
}
