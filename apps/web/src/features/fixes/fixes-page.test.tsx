import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "@/stores/session";
import { mockFetch, renderWithProviders } from "@/test/utils";
import { FixesPage } from "./fixes-page";

const mockSites = [
  {
    id: "site-1",
    name: "Acme Store",
    domain: "acme.com",
    homepage_url: "https://acme.com",
    platform: "shopify",
    primary_language: "en",
    additional_languages: [],
    brand_names: { en: ["Acme"] },
    competitor_domains: [],
  },
];

const mockFixes = [
  {
    id: "fix-1",
    site_id: "site-1",
    diagnosis_id: null,
    type: "schema",
    target_url: "https://acme.com",
    language: "en",
    title: "Add Organization Schema Markup",
    description: "Improves AI entity resolution",
    payload: {
      json_ld: {
        "@context": "https://schema.org",
        "@type": "Organization",
        name: "Acme Store",
      },
    },
    recommended_delivery: "snippet",
    status: "proposed",
    deployed_via: null,
    deployed_at: null,
    previous_state: null,
    created_at: "2026-10-01T10:00:00Z",
    updated_at: "2026-10-01T10:00:00Z",
  },
];

function api(url: string, _init: RequestInit) {
  if (url.endsWith("/sites")) return { body: mockSites };
  if (url.includes("/fixes/fix-1/approve")) {
    return { status: 200, body: { ...mockFixes[0], status: "approved" } };
  }
  if (url.includes("/fixes")) return { body: mockFixes };
  return undefined;
}

describe("FixesPage", () => {
  beforeEach(() => {
    useSession.setState({
      currentOrgId: "org-1",
      csrfToken: "csrf",
      user: {
        id: "u-1",
        email: "alice@example.com",
        full_name: "Alice",
        ui_language: "en",
        email_verified: true,
        is_platform_admin: false,
        has_password: true,
      },
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("renders proposed fixes with title and payload preview", async () => {
    mockFetch(api);
    renderWithProviders(<FixesPage />);

    expect(await screen.findByText("Add Organization Schema Markup")).toBeInTheDocument();
    expect(screen.getByText("schema")).toBeInTheDocument();
    expect(screen.getByText("Approve")).toBeInTheDocument();
    expect(screen.getByText("Reject")).toBeInTheDocument();
  });

  it("approves a proposed fix when verified user clicks Approve", async () => {
    mockFetch(api);
    const user = userEvent.setup();
    renderWithProviders(<FixesPage />);

    const approveBtn = await screen.findByRole("button", { name: /^approve$/i });
    expect(approveBtn).not.toBeDisabled();
    await user.click(approveBtn);

    await waitFor(() => {
      expect(approveBtn).toBeInTheDocument();
    });
  });

  it("displays warning when user email is unverified", async () => {
    useSession.setState({
      user: {
        id: "u-1",
        email: "unverified@example.com",
        full_name: "Bob",
        ui_language: "en",
        email_verified: false,
        is_platform_admin: false,
        has_password: true,
      },
    });
    mockFetch(api);
    renderWithProviders(<FixesPage />);

    expect(await screen.findByText(/Email verification is required/i)).toBeInTheDocument();
    const approveBtn = await screen.findByRole("button", { name: /^approve$/i });
    expect(approveBtn).toBeDisabled();
  });
});
