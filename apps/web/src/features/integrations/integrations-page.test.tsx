import { screen } from "@testing-library/react";
import { useSession } from "@/stores/session";
import { mockFetch, renderWithProviders } from "@/test/utils";
import { IntegrationsPage } from "./integrations-page";

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

const mockVerification = {
  domain: "acme.com",
  verified: false,
  verified_at: null,
  verification_method: null,
  token: "token-12345",
  meta_tag: '<meta name="omnirank-verification" content="token-12345">',
  dns_txt_record: "omnirank-verification=token-12345",
};

const mockSnippet = {
  site_key: "ors_abc123",
  script_url: "http://api.test/public/v1/agent.js",
  snippet_tag:
    '<script async src="http://api.test/public/v1/agent.js" data-site="ors_abc123"></script>',
  platform: "shopify",
  instructions: {
    wordpress: "Install the OmniRank plugin.",
    shopify: "Paste into theme.liquid before </head>.",
  },
};

const mockApiKeys = [
  {
    id: "key-1",
    name: "Production Next.js Key",
    prefix: "ql_live_abc",
    scopes: ["fixes:read"],
    last_used_at: null,
    created_at: "2026-10-01T10:00:00Z",
  },
];

const mockWebhooks = [
  {
    id: "wh-1",
    url: "https://myshop.com/webhook",
    status: "active",
    secret: "secret123",
    events: ["fix.created", "fix.deployed"],
    last_delivery_at: null,
    last_status_code: null,
    created_at: "2026-10-01T10:00:00Z",
  },
];

function api(url: string, _init: RequestInit) {
  if (url.endsWith("/sites")) return { body: mockSites };
  if (url.includes("/verification")) return { body: mockVerification };
  if (url.includes("/integrations/snippet")) return { body: mockSnippet };
  if (url.endsWith("/integrations")) return { body: [] };
  if (url.endsWith("/org/api-keys")) return { body: mockApiKeys };
  if (url.endsWith("/org/webhooks")) return { body: mockWebhooks };
  return undefined;
}

describe("IntegrationsPage", () => {
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

  it("renders verification meta tag, DNS TXT, deep platform integrations, snippet, and API keys", async () => {
    mockFetch(api);
    renderWithProviders(<IntegrationsPage />);

    expect(await screen.findByText(/Domain Ownership Verification/i)).toBeInTheDocument();
    expect(await screen.findByText(/omnirank-verification=token-12345/i)).toBeInTheDocument();
    expect(await screen.findByText(/Deep Platform Integrations/i)).toBeInTheDocument();
    expect(await screen.findByText(/OmniRank WordPress Plugin/i)).toBeInTheDocument();
    expect(await screen.findByText(/Universal JavaScript Snippet/i)).toBeInTheDocument();
    expect(screen.getByText(/ors_abc123/i)).toBeInTheDocument();
    expect(await screen.findByText("Production Next.js Key")).toBeInTheDocument();
    expect(await screen.findByText("https://myshop.com/webhook")).toBeInTheDocument();
  });
});
