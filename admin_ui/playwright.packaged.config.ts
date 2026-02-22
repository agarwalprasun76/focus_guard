import { defineConfig, devices } from "@playwright/test";

const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env ?? {};
const packagedBaseUrl = env.PACKAGED_ADMIN_BASE_URL ?? "http://127.0.0.1:58393";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  use: {
    baseURL: packagedBaseUrl,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "packaged-desktop-chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "packaged-mobile-safari",
      use: { ...devices["iPhone 13"] },
    },
  ],
});
