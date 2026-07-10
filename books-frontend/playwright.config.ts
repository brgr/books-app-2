import { defineConfig, devices } from "@playwright/test";

// End-to-end tests run against the real backend + frontend dev servers.
// If the servers are already running (the usual local dev case) they are reused;
// otherwise Playwright starts them.
// noinspection JSUnusedGlobalSymbols -- consumed by the Playwright runner
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "uv run fastapi dev main.py",
      cwd: "../books-backend",
      url: "http://localhost:8000/docs",
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
