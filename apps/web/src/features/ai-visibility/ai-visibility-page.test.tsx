import { screen } from "@testing-library/react";
import { useSession } from "@/stores/session";
import { mockFetch, renderWithProviders } from "@/test/utils";
import { AiVisibilityPage } from "./ai-visibility-page";

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

const mockAiVisibility = {
  overall_share_of_voice: 42.5,
  brand_mention_rate: 65.0,
  citation_rate: 30.0,
  prompts: [
    {
      id: "pr-1",
      prompt_text: "What are the best running shoes?",
      language: "en",
      country: "US",
      intent: "commercial",
      status: "active",
      brand_mentioned: true,
      site_cited: true,
      engines_status: {
        chatgpt: { mentioned: true, cited: true, sentiment: "positive" },
        gemini: { mentioned: true, cited: false, sentiment: "neutral" },
      },
      last_checked_at: "2026-10-01T10:00:00Z",
    },
  ],
  competitor_leaderboard: [{ domain: "rival.com", mentions: 12, share_pct: 35.0 }],
  per_engine: {
    chatgpt: 50.0,
    gemini: 35.0,
  },
};

function api(url: string, _init: RequestInit) {
  if (url.endsWith("/sites")) return { body: mockSites };
  if (url.includes("/ai-visibility")) return { body: mockAiVisibility };
  return undefined;
}

describe("AiVisibilityPage", () => {
  beforeEach(() => useSession.setState({ currentOrgId: "org-1", csrfToken: "csrf" }));
  afterEach(() => vi.unstubAllGlobals());

  it("renders metrics, prompt matrix, and competitor leaderboard", async () => {
    mockFetch(api);
    renderWithProviders(<AiVisibilityPage />);

    expect(await screen.findByText("What are the best running shoes?")).toBeInTheDocument();
    expect(screen.getByText("42.5%")).toBeInTheDocument();
    expect(screen.getByText("65%")).toBeInTheDocument();
    expect(screen.getByText("30%")).toBeInTheDocument();
    expect(screen.getByText("rival.com")).toBeInTheDocument();
  });
});
