import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "@/stores/session";
import { mockFetch, renderWithProviders } from "@/test/utils";
import { AuditsPage } from "./audits-page";

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

const mockAudits = [
  {
    id: "audit-1",
    site_id: "site-1",
    org_id: "org-1",
    status: "completed",
    score: 85,
    category_scores: {
      technical: 90,
      content: 80,
      ai_readiness: 85,
      performance: 85,
    },
    issues: [
      {
        id: "issue-1",
        category: "technical",
        title: "SSL Certificate Valid",
        severity: "info",
        description: "HTTPS is active",
        recommendation: "Maintain certificate renewal",
        affected_urls: [],
        passed: true,
      },
      {
        id: "issue-2",
        category: "content",
        title: "Missing Meta Description",
        severity: "warning",
        description: "Homepage meta description is empty",
        recommendation: "Add descriptive meta tag",
        affected_urls: ["https://acme.com"],
        passed: false,
      },
    ],
    summary: "Website SEO and AI readiness score is strong.",
    summary_ar: "مؤشر صحة الموقع ممتاز.",
    pages_crawled: 5,
    started_at: "2026-10-01T10:00:00Z",
    completed_at: "2026-10-01T10:01:00Z",
    error_message: null,
    created_at: "2026-10-01T10:00:00Z",
  },
];

function api(url: string, init?: RequestInit) {
  if (url.endsWith("/sites")) return { body: mockSites };
  if (url.includes("/audits") && init?.method === "POST") {
    return { status: 200, body: mockAudits[0] };
  }
  if (url.includes("/audits")) return { body: mockAudits };
  return undefined;
}

describe("AuditsPage", () => {
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

  it("renders audit score and category breakdown", async () => {
    renderWithProviders(<AuditsPage />);

    await waitFor(() => {
      expect(screen.getByText("85")).toBeInTheDocument();
      expect(screen.getByText(/SSL Certificate Valid/i)).toBeInTheDocument();
      expect(screen.getByText(/Missing Meta Description/i)).toBeInTheDocument();
    });
  });

  it("triggers a new audit when Run Audit is clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AuditsPage />);

    await waitFor(() => expect(screen.getByText("85")).toBeInTheDocument());

    const runBtn = screen.getByRole("button", { name: /Run Audit/i });
    await user.click(runBtn);

    await waitFor(() => {
      expect(screen.getByText(/Website SEO and AI readiness/i)).toBeInTheDocument();
    });
  });
});
