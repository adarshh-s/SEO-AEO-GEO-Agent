import { expect, test } from "@playwright/test";

test("sign up, onboard a website, see it listed, switch to Arabic", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;
  const domain = `e2e-${Date.now()}.example.com`;

  await page.goto("/signup");
  await page.getByLabel("Your name").fill("E2E Tester");
  await page.getByLabel("Company name").fill("E2E Co");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("a-very-good-password");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/app\/onboarding/);
  await page.getByLabel("Website address").fill(domain);
  await page.getByRole("button", { name: "Analyze" }).click();
  await expect(page.getByText(/Sample data/)).toBeVisible();
  await page.getByLabel("Industry").fill("dental clinic");
  await page.getByRole("button", { name: "Next" }).click();

  await expect(page.getByRole("checkbox", { name: /Add Arabic/ })).not.toBeChecked();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByText("Keywords to track in Google")).toBeVisible();
  await page.getByRole("button", { name: "Save and continue" }).click();

  await expect(page.getByText("Connect your website")).toBeVisible();
  await expect(page.getByText(/data-site="ors_/)).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Go to dashboard" }).click();

  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.getByRole("link", { name: "Websites" }).first().click();
  await expect(page.getByText(domain)).toBeVisible();

  await page.getByRole("button", { name: /العربية/ }).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { name: "المواقع" })).toBeVisible();

  // The choice is saved per user: still Arabic after a reload.
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
});
