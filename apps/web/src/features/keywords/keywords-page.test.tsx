import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "@/stores/session";
import { mockFetch, renderWithProviders } from "@/test/utils";
import { KeywordsPage } from "./keywords-page";

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
    competitor_domains: ["rival.com"],
  },
];

const mockRankings = [
  {
    id: "kw-1",
    keyword: "best shoes",
    language: "en",
    country: "US",
    device: "desktop",
    status: "active",
    position: 3,
    previous_position: 5,
    position_change: 2,
    url_ranked: "https://acme.com/shoes",
    serp_features: ["featured_snippet", "ai_overview"],
    ai_overview_present: true,
    ai_overview_cites_site: true,
    last_checked_at: "2026-10-01T10:00:00Z",
  },
];

function api(url: string, _init: RequestInit) {
  if (url.endsWith("/sites")) return { body: mockSites };
  if (url.includes("/rankings")) return { body: mockRankings };
  if (url.includes("/keywords/kw-1/check")) return { status: 200, body: { ok: true } };
  return undefined;
}

describe("KeywordsPage", () => {
  beforeEach(() => useSession.setState({ currentOrgId: "org-1", csrfToken: "csrf" }));
  afterEach(() => vi.unstubAllGlobals());

  it("renders tracked keywords with position, change, and AI Overview", async () => {
    mockFetch(api);
    renderWithProviders(<KeywordsPage />);

    expect(await screen.findByText("best shoes")).toBeInTheDocument();
    expect(screen.getByText(/3/)).toBeInTheDocument();
    expect(screen.getByText(/\+2/)).toBeInTheDocument();
    expect(screen.getAllByText("AI Overview").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Cites your site")).toBeInTheDocument();
  });

  it("triggers a keyword check when the refresh button is clicked", async () => {
    const calls = mockFetch(api);
    renderWithProviders(<KeywordsPage />);

    expect(await screen.findByText("best shoes")).toBeInTheDocument();
    const checkBtn = screen.getByRole("button", { name: "Check now" });
    await userEvent.click(checkBtn);
    await waitFor(() => {
      expect(calls.some((c) => c.url.includes("/keywords/kw-1/check"))).toBe(true);
    });
  });
});
