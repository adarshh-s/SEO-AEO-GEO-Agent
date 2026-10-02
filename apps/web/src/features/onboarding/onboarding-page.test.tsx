import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "@/stores/session";
import { mockFetch, renderWithProviders } from "@/test/utils";
import type { CompleteIn } from "@/lib/api-types";
import { OnboardingPage } from "./onboarding-page";

const analysis = {
  source: "mock",
  homepage_url: "https://smile.sa/",
  domain: "smile.sa",
  platform: "salla",
  brand_name: "Smile",
  detected_languages: ["en", "ar"],
  industry: null,
  city: "Riyadh",
  country: "SA",
  competitors: [],
};

function api(url: string, init: RequestInit) {
  const body = init.body ? JSON.parse(String(init.body)) : {};
  if (url.endsWith("/onboarding/analyze")) return { body: analysis };
  if (url.endsWith("/onboarding/suggestions")) {
    const kw = body.languages.map((l: string) => ({ keyword: `kw-${l}`, language: l }));
    const pr = body.languages.map((l: string) => ({
      prompt_text: `prompt-${l}`,
      language: l,
      intent: "local",
    }));
    return { body: { source: "mock", keywords: kw, prompts: pr } };
  }
  if (url.endsWith("/onboarding/complete")) {
    return {
      status: 201,
      body: {
        id: "s1",
        platform: "salla",
        site_key: "qls_abc123",
        verification_token: "tok456",
        ...body.site,
      },
    };
  }
  if (url.endsWith("/org"))
    return {
      body: {
        plan: { name: "Trial", trial_days: 14, max_sites: 1, max_keywords: 25, max_prompts: 10 },
      },
    };
  return undefined;
}

describe("OnboardingPage", () => {
  beforeEach(() => useSession.setState({ currentOrgId: "o1", csrfToken: "c" }));
  afterEach(() => vi.unstubAllGlobals());

  it("runs the wizard with English only by default (Arabic is opt-in)", async () => {
    const calls = mockFetch(api);
    renderWithProviders(<OnboardingPage />);

    await userEvent.type(screen.getByLabelText("Website address"), "smile.sa");
    await userEvent.click(screen.getByRole("button", { name: "Analyze" }));
    expect(await screen.findByText(/Sample data/)).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Industry"), "dentist");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    const arabic = await screen.findByRole("checkbox", { name: /Add Arabic/ });
    expect(arabic).not.toBeChecked();
    expect(screen.getByText(/We found Arabic content/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(await screen.findByText("kw-en")).toBeInTheDocument();
    expect(screen.queryByText("kw-ar")).not.toBeInTheDocument();
    expect(calls.find((c) => c.url.endsWith("/suggestions"))?.body).toMatchObject({
      languages: ["en"],
    });

    await userEvent.click(screen.getByRole("button", { name: "Save and continue" }));
    await waitFor(() => expect(calls.some((c) => c.url.endsWith("/complete"))).toBe(true));
    const complete = calls.find((c) => c.url.endsWith("/complete"))!.body as CompleteIn;
    expect(complete.site).toMatchObject({
      primary_language: "en",
      additional_languages: [],
      platform: "salla",
      industry: "dentist",
    });
    expect(complete.keywords).toEqual([
      { keyword: "kw-en", language: "en", device: "desktop", tags: [] },
    ]);

    expect(await screen.findByText("Connect your website")).toBeInTheDocument();
    expect(screen.getByText(/data-site="qls_abc123"/)).toBeInTheDocument();
    expect(screen.getByText(/omnirank-verification/)).toBeInTheDocument();
    expect(screen.getByText(/Many AI crawlers don't run JavaScript/)).toBeInTheDocument();
  });

  it("adds Arabic tracking and brand name when opted in", async () => {
    const calls = mockFetch(api);
    renderWithProviders(<OnboardingPage />);
    await userEvent.type(screen.getByLabelText("Website address"), "smile.sa");
    await userEvent.click(screen.getByRole("button", { name: "Analyze" }));
    await userEvent.type(await screen.findByLabelText("Industry"), "dentist");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await userEvent.click(await screen.findByRole("checkbox", { name: /Add Arabic/ }));
    await userEvent.type(screen.getByLabelText("Brand name in Arabic"), "سمايل");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("kw-ar")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Save and continue" }));
    await waitFor(() => expect(calls.some((c) => c.url.endsWith("/complete"))).toBe(true));
    const complete = calls.find((c) => c.url.endsWith("/complete"))!.body as CompleteIn;
    expect(complete.site.additional_languages).toEqual(["ar"]);
    expect(complete.site.brand_names).toEqual({ en: ["Smile"], ar: ["سمايل"] });
  });
});
