import { defineConfig, devices } from "@playwright/test";
import baseConfig from "./playwright.config";

const systemPort = process.env.PLAYWRIGHT_PORT ?? "3100";
const systemBaseUrl = `http://localhost:${systemPort}`;

export default defineConfig({
  ...baseConfig,
  use: { ...baseConfig.use, baseURL: systemBaseUrl, trace: "off" },
  testDir: "./e2e",
  testMatch: ["system-golden-path.spec.ts", "hostile-input.spec.ts", "system-stress.spec.ts"],
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  reporter: process.env.CI ? "github" : "list",
  projects: [{ name: "chromium-system", use: { ...devices["Desktop Chrome"] } }],
  workers: 1,
  webServer: {
    command: `npm run start -- --hostname localhost --port ${systemPort}`,
    url: `${systemBaseUrl}/admin/login`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      ADMIN_SESSION_SECRET: process.env.ADMIN_SESSION_SECRET ?? "",
      NEXT_TELEMETRY_DISABLED: "1",
      P13_SYSTEM_TEST_MODE: process.env.P13_SYSTEM_TEST_MODE ?? "",
      APP_ENV: process.env.APP_ENV ?? "local",
      SITE_URL: process.env.SITE_URL ?? "",
      RELEASE_COMMIT_SHA: process.env.RELEASE_COMMIT_SHA ?? "",
      BUILD_TIMESTAMP: process.env.BUILD_TIMESTAMP ?? "",
      TRUST_PROXY_HEADERS: process.env.TRUST_PROXY_HEADERS ?? "",
      RATE_LIMIT_HASH_SECRET: process.env.RATE_LIMIT_HASH_SECRET ?? "",
      UPSTASH_REDIS_REST_URL: process.env.UPSTASH_REDIS_REST_URL ?? "",
      UPSTASH_REDIS_REST_TOKEN: process.env.UPSTASH_REDIS_REST_TOKEN ?? "",
    },
  },
});
