import { defineConfig, devices } from "@playwright/test";
import { BACKEND_PORT, E2E_DB_URL, FRONTEND_PORT } from "./support/config";

// End-to-end tests run against dedicated servers on isolated ports, backed by a throwaway
// database (books-e2e.db) that `global-setup` seeds from the sample fixture. This keeps the
// suite deterministic. The server is not reused, so each run binds the freshly seeded DB.

// noinspection JSUnusedGlobalSymbols -- consumed by the Playwright runner
export default defineConfig({
  testDir: "./specs",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  globalSetup: "./support/global-setup.ts",
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `uv run fastapi dev main.py --port ${BACKEND_PORT}`,
      cwd: "../books-backend",
      env: {
        DATABASE_URL: E2E_DB_URL,
        // The e2e frontend runs on 5174, so CORS must allow that origin for credentialed requests
        ALLOWED_ORIGINS: `http://localhost:${FRONTEND_PORT},http://127.0.0.1:${FRONTEND_PORT}`,
      },
      url: `http://localhost:${BACKEND_PORT}/docs`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npm run dev -- --port ${FRONTEND_PORT}`,
      cwd: "../books-frontend",
      env: { VITE_API_URL: `http://localhost:${BACKEND_PORT}` },
      url: `http://localhost:${FRONTEND_PORT}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
