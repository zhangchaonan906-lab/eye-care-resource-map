import { defineConfig, devices } from "@playwright/test";
import { randomBytes } from "node:crypto";

const port = Number(process.env.PLAYWRIGHT_PORT ?? 3100);
const baseURL = `http://127.0.0.1:${port}`;
const adminSessionSecret = process.env.ADMIN_SESSION_SECRET ?? randomBytes(32).toString("hex");
process.env.ADMIN_SESSION_SECRET = adminSessionSecret;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: `npm run start -- --hostname 127.0.0.1 --port ${port}`,
    url: `${baseURL}/admin/login`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      ADMIN_SESSION_SECRET: adminSessionSecret,
      NEXT_TELEMETRY_DISABLED: "1",
    },
  },
});
