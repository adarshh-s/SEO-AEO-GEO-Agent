import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { applyLanguage } from "@/lib/i18n";
import { useSession } from "@/stores/session";
import { mockFetch, renderWithProviders } from "@/test/utils";
import { LanguageToggle } from "./language-toggle";

const user = {
  id: "u1",
  email: "a@b.co",
  full_name: "A",
  ui_language: "en",
  is_platform_admin: false,
  email_verified: true,
  has_password: true,
};

describe("LanguageToggle", () => {
  afterEach(async () => {
    await applyLanguage("en");
    useSession.getState().clear();
    vi.unstubAllGlobals();
  });

  it("switches to Arabic (RTL) and back without saving when signed out", async () => {
    const calls = mockFetch(() => undefined);
    renderWithProviders(<LanguageToggle />);
    await userEvent.click(screen.getByRole("button", { name: /العربية/ }));
    expect(document.documentElement.dir).toBe("rtl");
    await userEvent.click(screen.getByRole("button", { name: /English/ }));
    expect(document.documentElement.dir).toBe("ltr");
    expect(calls).toHaveLength(0);
  });

  it("saves the choice per user when signed in", async () => {
    useSession.getState().setSession({ user, orgs: [], csrf_token: "csrf" });
    const calls = mockFetch((url) =>
      url.endsWith("/auth/me") ? { body: { ...user, ui_language: "ar" } } : undefined,
    );
    renderWithProviders(<LanguageToggle />);
    await userEvent.click(screen.getByRole("button", { name: /العربية/ }));
    expect(calls[0]).toMatchObject({ method: "PATCH", body: { ui_language: "ar" } });
    expect(useSession.getState().user?.ui_language).toBe("ar");
  });
});
