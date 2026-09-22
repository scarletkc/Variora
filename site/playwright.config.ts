import { defineConfig, devices } from "@playwright/test";

const development = process.env.VARIORA_E2E_SERVER === "dev";

export default defineConfig({
  testDir: "./tests/browser",
  fullyParallel: true,
  workers: process.env.CI ? 2 : 4,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:4173", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    {
      name: "mobile",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" },
    },
  ],
  webServer: {
    command: development
      ? "next dev --hostname 127.0.0.1 --port 4173"
      : "node scripts/serve.mjs",
    // Compile the preview route before parallel development checks begin.
    url: `http://127.0.0.1:4173/en/${development ? "preview/" : ""}`,
    reuseExistingServer: false,
  },
});
