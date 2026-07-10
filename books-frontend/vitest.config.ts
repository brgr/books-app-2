import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: "jsdom",
    setupFiles: ["fake-indexeddb/auto"],
    // Playwright specs under e2e/ are run by the Playwright runner, not vitest.
    exclude: ["**/node_modules/**", "**/dist/**", "e2e/**"],
  },
});
