import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "@/stores/session";
import { mockFetch, renderWithProviders } from "@/test/utils";
import { AdminPage } from "./admin-page";

const mockOrgs = [
  {
    id: "org-1",
    name: "Acme Corp",
    slug: "acme-corp",
    plan_code: "starter",
    addons: { arabic: true },
    cost_ceiling_override_usd: 50.0,
    members: 3,
    sites: 1,
    created_at: "2026-10-01T10:00:00Z",
    current_spend_usd: 12.5,
    effective_ceiling_usd: 50.0,
    spend_ratio: 0.25,
    is_trial_expired: false,
  },
];

const mockPlans = [
  {
    code: "starter",
    name: "Starter",
    sort_order: 1,
    is_public: true,
    max_sites: 1,
    max_keywords: 50,
    max_prompts: 20,
    max_engines: 2,
    allowed_engines: ["chatgpt", "gemini"],
    max_languages_per_site: 1,
    addon_languages: ["ar"],
    check_frequency: "weekly",
    audits_per_month: 2,
    trial_days: null,
    monthly_cost_ceiling_usd: 15.0,
  },
  {
    code: "growth",
    name: "Growth",
    sort_order: 2,
    is_public: true,
    max_sites: 5,
    max_keywords: 200,
    max_prompts: 80,
    max_engines: 4,
    allowed_engines: ["chatgpt", "gemini", "claude", "perplexity"],
    max_languages_per_site: 3,
    addon_languages: ["ar"],
    check_frequency: "twice_weekly",
    audits_per_month: 10,
    trial_days: null,
    monthly_cost_ceiling_usd: 60.0,
  },
];

const mockCostSummary = {
  total_spend_usd: 12.5,
  total_orgs: 1,
  orgs_at_warning: 0,
  orgs_at_paused: 0,
  provider_breakdown: { openai: 10.0, dataforseo: 2.5 },
  category_breakdown: { ai_check: 10.0, serp: 2.5 },
  top_spending_orgs: [
    {
      org_id: "org-1",
      name: "Acme Corp",
      slug: "acme-corp",
      plan_code: "starter",
      spend_usd: "12.50",
      ceiling_usd: "50.00",
      ratio: 0.25,
    },
  ],
};

function api(url: string, init?: RequestInit) {
  if (url.endsWith("/admin/orgs")) return { body: mockOrgs };
  if (url.endsWith("/admin/plans")) return { body: mockPlans };
  if (url.endsWith("/admin/costs/summary")) return { body: mockCostSummary };
  if (url.includes("/admin/orgs/org-1/plan") && init?.method === "PUT") {
    return { status: 200, body: { ...mockOrgs[0], plan_code: "growth" } };
  }
  return undefined;
}

describe("AdminPage", () => {
  beforeEach(() => {
    useSession.setState({
      currentOrgId: "org-1",
      csrfToken: "csrf",
      user: {
        id: "admin-user",
        email: "admin@example.com",
        full_name: "Admin User",
        ui_language: "en",
        is_platform_admin: true,
        email_verified: true,
        has_password: true,
      },
    });
    mockFetch(api);
  });

  it("renders organizations list with spend and plan controls", async () => {
    renderWithProviders(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByText("Acme Corp")).toBeInTheDocument();
      expect(screen.getByText("$12.50")).toBeInTheDocument();
      expect(screen.getByText("Normal")).toBeInTheDocument();
    });
  });

  it("switches to API Costs tab and renders provider breakdown", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AdminPage />);

    await waitFor(() => expect(screen.getByText("Acme Corp")).toBeInTheDocument());

    const costsTab = screen.getByRole("button", { name: /API Costs/i });
    await user.click(costsTab);

    await waitFor(() => {
      expect(screen.getByText(/Total Platform Spend/i)).toBeInTheDocument();
      expect(screen.getByText("openai")).toBeInTheDocument();
      expect(screen.getByText("dataforseo")).toBeInTheDocument();
    });
  });
});
