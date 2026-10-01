import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "@/stores/session";
import { mockFetch, renderWithProviders } from "@/test/utils";
import { ReportsPage } from "./reports-page";

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

const mockReports = [
  {
    id: "rep-1",
    site_id: "site-1",
    org_id: "org-1",
    audit_id: "audit-1",
    report_type: "executive",
    title: "Executive SEO & AI Scorecard",
    language: "en",
    status: "completed",
    metrics_summary: { score: 85 },
    created_at: "2026-10-01T10:00:00Z",
  },
];

function api(url: string, init?: RequestInit) {
  if (url.endsWith("/sites")) return { body: mockSites };
  if (url.includes("/reports/digest/send-test") && init?.method === "POST") {
    return {
      status: 200,
      body: { ok: true, message: "Weekly digest sent", recipient: "test@example.com" },
    };
  }
  if (url.includes("/reports") && init?.method === "POST") {
    return { status: 200, body: mockReports[0] };
  }
  if (url.includes("/reports")) return { body: mockReports };
  return undefined;
}

describe("ReportsPage", () => {
  beforeEach(() => {
    useSession.setState({
      currentOrgId: "org-1",
      csrfToken: "csrf",
      user: {
        id: "u-1",
        email: "test@example.com",
        full_name: "Test",
        ui_language: "en",
        is_platform_admin: false,
        email_verified: true,
        has_password: true,
      },
    });
    mockFetch(api);
  });

  it("renders report list and allows downloading PDF", async () => {
    renderWithProviders(<ReportsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Executive SEO & AI Scorecard/i)).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Download PDF/i })).toHaveAttribute(
        "href",
        "/api/sites/site-1/reports/rep-1/download",
      );
    });
  });

  it("sends test email digest", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ReportsPage />);

    await waitFor(() =>
      expect(screen.getByText(/Executive SEO & AI Scorecard/i)).toBeInTheDocument(),
    );

    const sendBtn = screen.getByRole("button", { name: /Send Test Digest/i });
    await user.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText(/Weekly digest sent/i)).toBeInTheDocument();
    });
  });
});
