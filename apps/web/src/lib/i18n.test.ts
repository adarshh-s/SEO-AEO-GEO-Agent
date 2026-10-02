import { PRODUCT_NAME } from "./brand";
import i18n, { applyLanguage, formatNumber, isRtl, SUPPORTED_LANGUAGES } from "./i18n";

describe("i18n", () => {
  afterEach(async () => {
    await applyLanguage("en");
  });

  it("defaults to English and discovers locales from folders", () => {
    expect(i18n.language).toBe("en");
    expect(SUPPORTED_LANGUAGES[0]).toBe("en");
    expect(SUPPORTED_LANGUAGES).toContain("ar");
  });

  it("applies RTL only for Arabic", async () => {
    await applyLanguage("ar");
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ar");
    await applyLanguage("en");
    expect(document.documentElement.dir).toBe("ltr");
    expect(isRtl("ar-SA")).toBe(true);
    expect(isRtl("fr")).toBe(false);
  });

  it("falls back to English for missing Arabic keys and unknown languages", async () => {
    await applyLanguage("ar");
    expect(i18n.t("nav.signOut")).toBe("تسجيل الخروج");
    // The legal drafts are intentionally not translated yet.
    expect(i18n.t("privacy.title", { ns: "public" })).toBe("Privacy Policy");
    await applyLanguage("xx");
    expect(i18n.language).toBe("en");
  });

  it("fills the product name from brand config", () => {
    expect(i18n.t("login.description", { ns: "auth" })).toMatch(new RegExp(PRODUCT_NAME));
  });

  it("uses Western digits in Arabic (D9)", () => {
    expect(formatNumber(1234567, "ar")).toMatch(/1.?234.?567/);
    expect(formatNumber(12, "ar")).not.toMatch(/[٠-٩]/);
  });
});
