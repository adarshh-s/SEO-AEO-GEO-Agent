import { defineConfig, devices } from "@playwright/test";

// Dedicated ports so E2E never talks to some other dev server already on 5173/8000.
const API_PORT = Number(process.env.E2E_API_PORT ?? 8100);
const WEB_PORT = Number(process.env.E2E_WEB_PORT ?? 5273);

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : "list",
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `uv run uvicorn app_api.main:app --port ${API_PORT}`,
      cwd: "../..",
      url: `http://localhost:${API_PORT}/healthz`,
      reuseExistingServer: false,
      env: {
        EMAIL_PROVIDER: "console",
        AUTH_RATE_LIMIT_PER_MINUTE: "100",
        APP_URL: `http://localhost:${WEB_PORT}`,
        API_URL: `http://localhost:${API_PORT}`,
        CORS_ORIGINS: `http://localhost:${WEB_PORT}`,
      },
    },
    {
      command: `pnpm exec vite --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: false,
      env: { VITE_API_URL: `http://localhost:${API_PORT}` },
    },
  ],
});
