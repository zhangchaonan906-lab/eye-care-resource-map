import { createHmac, randomBytes } from "node:crypto";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const facilityId = "123e4567-e89b-42d3-a456-426614174000";
const xssName = '<img src=x onerror="alert(1)">眼科测试中心';
const facility = {
  id: facilityId,
  name: xssName,
  category: "ophthalmology_center",
  address: "北京市东城区测试路 1 号",
  region: { adcode: "110101", name: "北京市东城区" },
  hospitalLevel: null,
  hospitalGrade: null,
  longitude: 116.4074,
  latitude: 39.9042,
  ophthalmology: { status: "verified", evidenceCount: 1 },
  attribution: [
    { name: "测试官方来源", url: "javascript:alert(1)", updatedAt: null },
    { name: "测试数据链接", url: "data:text/html,<script>alert(2)</script>", updatedAt: null },
  ],
  lastVerifiedAt: "2026-09-01T00:00:00.000Z",
};

async function mockPublicApi(page: Page) {
  await page.route("**/api/meta/categories", (route) => route.fulfill({
    json: { data: [{ id: "ophthalmology_center", label: "眼科中心" }], meta: { publishedFacilityCount: 1 } },
  }));
  await page.route(`**/api/facilities/${facilityId}`, (route) => route.fulfill({ json: { data: facility } }));
  await page.route("**/api/facilities?**", (route) => route.fulfill({
    json: { data: [facility], meta: { nextCursor: null } },
  }));
  await page.route("**/api/search?**", (route) => route.fulfill({
    json: { data: [facility], meta: { nextCursor: null } },
  }));
  await page.route("**/api/nearby", (route) => route.fulfill({
    json: { data: [{ ...facility, distanceMeters: 1200 }], meta: { truncated: false } },
  }));
}

async function axeViolations(page: Page) {
  return new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
}

function createAdminCookie(secret: string, csrfToken: string) {
  const payload = Buffer.from(JSON.stringify({
    actorId: "123e4567-e89b-42d3-a456-426614174111",
    username: "p13-reviewer",
    role: "admin",
    expiresAt: Date.now() + 60_000,
    csrfToken,
  })).toString("base64url");
  return `${payload}.${createHmac("sha256", secret).update(payload).digest("base64url")}`;
}

test.describe("P13 public browser QA", () => {
  test("direct map route, search, XSS text handling, detail panel and source URL safety @a11y", async ({ page }) => {
    await mockPublicApi(page);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/resources/eye-hospitals");

    await expect(page.getByRole("heading", { name: "全国眼科医疗资源地图" })).toBeVisible();
    await expect(page.getByRole("region", { name: "医疗机构地图" })).toBeVisible();
    await expect(page.locator(".maplibregl-canvas")).toBeVisible();
    await expect(page.getByText(/实际展示范围取决于已核验公开数据/)).toBeVisible();
    await expect(page.getByRole("searchbox", { name: "搜索医院" })).toBeVisible();
    await page.getByRole("searchbox", { name: "搜索医院" }).fill("测试中心");
    await expect(page.getByRole("button", { name: new RegExp("眼科测试中心") })).toBeVisible();
    await page.getByRole("button", { name: new RegExp("眼科测试中心") }).click();

    const panel = page.getByRole("dialog");
    await expect(panel).toBeVisible();
    await expect(panel.getByRole("heading", { name: xssName })).toBeFocused();
    await expect(panel.locator("img")).toHaveCount(0);
    await expect(panel).toContainText(xssName);
    await expect(panel.getByText("测试官方来源")).toBeVisible();
    await expect(panel.getByText("测试数据链接")).toBeVisible();
    await expect(panel.getByRole("link", { name: "测试官方来源" })).toHaveCount(0);
    await expect(panel.getByRole("link", { name: "测试数据链接" })).toHaveCount(0);
    await page.getByRole("button", { name: "关闭详情" }).click();
    await expect(page.getByRole("searchbox", { name: "搜索医院" })).toBeFocused();

    const result = await axeViolations(page);
    const seriousOrCritical = result.violations.filter((item) => ["serious", "critical"].includes(item.impact ?? ""));
    expect(seriousOrCritical, JSON.stringify(seriousOrCritical, null, 2)).toEqual([]);
  });

  test("mobile map controls and list remain usable without hover", async ({ page }) => {
    await mockPublicApi(page);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/resources/eye-hospitals");
    const search = page.getByRole("searchbox", { name: "搜索医院" });
    await expect(search).toBeVisible();
    await search.fill("测试中心");
    const result = page.getByRole("button", { name: new RegExp("眼科测试中心") });
    await expect(result).toBeVisible();
    await result.focus();
    await expect(result).toBeFocused();
    await result.click();
    const panel = page.getByRole("dialog");
    await expect(panel).toBeVisible();
    await expect(panel.getByRole("heading", { name: xssName })).toBeFocused();
    await expect(page.getByRole("button", { name: "关闭详情" })).toBeVisible();
    await page.getByRole("button", { name: "关闭详情" }).click();
    await expect(search).toBeFocused();
  });

  test("nearby uses granted geolocation in memory and does not persist it in browser state", async ({ page, context }) => {
    await mockPublicApi(page);
    await context.grantPermissions(["geolocation"]);
    await context.setGeolocation({ latitude: 39.9042, longitude: 116.4074 });
    await page.goto("/resources/eye-hospitals");
    await page.getByRole("button", { name: "定位到我" }).click();
    await expect(page.getByRole("button", { name: "已定位" })).toBeVisible();
    await expect(page.getByRole("region", { name: "附近机构" })).toContainText("1.2 km");

    const browserState = await page.evaluate(() => ({
      href: window.location.href,
      localStorage: Object.keys(window.localStorage),
      sessionStorage: Object.keys(window.sessionStorage),
    }));
    expect(browserState.href).not.toContain("39.9042");
    expect(browserState.href).not.toContain("116.4074");
    expect(browserState.localStorage).toEqual([]);
    expect(browserState.sessionStorage).toEqual([]);
    expect(await context.cookies()).toEqual([]);

    const requestFor3km = page.waitForRequest((request) =>
      request.url().endsWith("/api/nearby") && request.method() === "POST" &&
      (request.postDataJSON() as { radius?: number } | null)?.radius === 3000,
    );
    await page.getByRole("combobox", { name: "附近搜索半径" }).selectOption("3000");
    const nearbyRequest = await requestFor3km;
    expect(nearbyRequest.url()).not.toContain("39.9042");
    expect(nearbyRequest.url()).not.toContain("116.4074");
    expect(nearbyRequest.postDataJSON()).toMatchObject({ lat: 39.9042, lng: 116.4074, radius: 3000 });
  });

  test("permission denial leaves the map and manual search usable", async ({ page, context }) => {
    await mockPublicApi(page);
    await context.grantPermissions([]);
    await page.goto("/resources/eye-hospitals");
    await page.getByRole("button", { name: "定位到我" }).click();
    await expect(page.getByText("定位权限未开启，你仍可以搜索或手动浏览地图。", { exact: true })).toBeVisible();
    await expect(page.getByRole("searchbox", { name: "搜索医院" })).toBeEnabled();
  });

  test("invalid and unpublished detail identifiers return not found", async ({ page }) => {
    const invalid = await page.goto("/hospitals/not-a-uuid");
    expect(invalid?.status()).toBe(404);
    await mockPublicApi(page);
    await page.route("**/api/facilities/123e4567-e89b-42d3-a456-426614174001", (route) => route.fulfill({
      status: 404,
      json: { error: { code: "NOT_FOUND", message: "机构不存在" } },
    }));
    await page.goto(`/resources/eye-hospitals?facility=123e4567-e89b-42d3-a456-426614174001`);
    await expect(page.getByText("该机构当前不可公开查看，仍可使用搜索或地图浏览。", { exact: true })).toBeVisible();
    await expect(page.getByText("123e4567-e89b-42d3-a456-426614174001")).toHaveCount(0);
  });
});

test.describe("P13 admin route accessibility", () => {
  test("admin login is direct-loadable, labeled and has no serious axe violations @a11y", async ({ page }) => {
    await page.goto("/admin/login");
    await expect(page.getByRole("heading", { name: "管理员登录" })).toBeVisible();
    await expect(page.getByRole("textbox", { name: "用户名" })).toBeVisible();
    await expect(page.getByLabel("密码")).toBeVisible();
    const result = await axeViolations(page);
    const seriousOrCritical = result.violations.filter((item) => ["serious", "critical"].includes(item.impact ?? ""));
    expect(seriousOrCritical, JSON.stringify(seriousOrCritical, null, 2)).toEqual([]);
  });

  test("admin console route is protected and authenticated shell is keyboard reachable @a11y", async ({ page }) => {
    await page.goto("/admin");
    await expect(page).toHaveURL(/\/admin\/login/);

    const secret = process.env.ADMIN_SESSION_SECRET;
    if (!secret) throw new Error("Playwright must provide an isolated admin session secret");
    const csrfToken = randomBytes(32).toString("base64url");
    await page.context().addCookies([
      { name: "eye_admin_session", value: createAdminCookie(secret, csrfToken), domain: "127.0.0.1", path: "/", httpOnly: true, sameSite: "Strict" },
      { name: "eye_admin_csrf", value: csrfToken, domain: "127.0.0.1", path: "/", sameSite: "Strict" },
    ]);
    await page.route("**/api/admin/**", (route) => route.fulfill({ json: { data: [], meta: { nextCursor: null } } }));
    await page.goto("/admin");
    await expect(page.getByRole("heading", { name: "审核控制台" })).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(page.locator(":focus")).not.toHaveCount(0);
    const result = await axeViolations(page);
    const seriousOrCritical = result.violations.filter((item) => ["serious", "critical"].includes(item.impact ?? ""));
    expect(seriousOrCritical, JSON.stringify(seriousOrCritical, null, 2)).toEqual([]);
  });
});
