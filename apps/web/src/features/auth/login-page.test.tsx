import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "@/stores/session";
import { mockFetch, renderWithProviders } from "@/test/utils";
import { LoginPage } from "./login-page";

describe("LoginPage", () => {
  afterEach(() => {
    useSession.getState().clear();
    vi.unstubAllGlobals();
  });

  it("validates fields before calling the API", async () => {
    const calls = mockFetch(() => undefined);
    renderWithProviders(<LoginPage />, { route: "/login" });
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findAllByText("This field is required.")).toHaveLength(2);
    expect(calls).toHaveLength(0);
  });

  it("shows a translated API error", async () => {
    mockFetch(() => ({
      status: 401,
      body: { detail: { code: "invalid_credentials", message: "x" } },
    }));
    renderWithProviders(<LoginPage />, { route: "/login" });
    await userEvent.type(screen.getByLabelText("Email"), "a@b.co");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Email or password is incorrect.")).toBeInTheDocument();
  });

  it("stores the session on success", async () => {
    const session = {
      user: {
        id: "u1",
        email: "a@b.co",
        full_name: "A",
        ui_language: "en",
        is_platform_admin: false,
        email_verified: true,
        has_password: true,
      },
      orgs: [{ id: "o1", name: "Acme", slug: "acme", role: "owner", plan_code: "trial" }],
      csrf_token: "csrf-1",
    };
    mockFetch((url) => (url.endsWith("/auth/login") ? { body: session } : undefined));
    renderWithProviders(<LoginPage />, { route: "/login" });
    await userEvent.type(screen.getByLabelText("Email"), "a@b.co");
    await userEvent.type(screen.getByLabelText("Password"), "correct-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(useSession.getState().csrfToken).toBe("csrf-1"));
    expect(useSession.getState().currentOrgId).toBe("o1");
  });
});
