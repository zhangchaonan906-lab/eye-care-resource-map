import { expect, test } from "@playwright/test";
import { Pool } from "pg";

const pool = new Pool({ connectionString: process.env.DATABASE_ADMIN_URL, max: 2 });
const unsafeLeak = /stack trace|postgres(?:ql)?|relation .* does not exist|app_private|source_records|SQLSTATE|syntax error|DROP TABLE/i;

async function login(page: import("@playwright/test").Page) {
  await page.goto("/admin/login");
  await page.getByLabel("用户名").fill(process.env.ADMIN_USERNAME!);
  await page.getByLabel("密码").fill(process.env.P13_ADMIN_PASSWORD!);
  await page.getByRole("button", { name: "登录审核台" }).click();
  await expect(page).toHaveURL(/\/admin$/);
}

async function browserRequest(page: import("@playwright/test").Page, path: string, method = "GET", body?: Record<string, unknown>) {
  return page.evaluate(async ({ requestPath, requestMethod, payload }) => {
    const tokenResult = await fetch("/api/admin/session", { cache: "no-store" }).then((response) => response.json());
    const headers: Record<string, string> = {};
    if (payload) {
      headers["Content-Type"] = "application/json";
      headers["X-CSRF-Token"] = tokenResult.data.csrfToken;
      headers["Idempotency-Key"] = crypto.randomUUID();
    }
    const response = await fetch(requestPath, {
      method: requestMethod,
      headers,
      body: payload ? JSON.stringify(payload) : undefined,
      cache: "no-store",
    });
    const text = await response.text();
    let result: unknown;
    try { result = JSON.parse(text); } catch { result = text; }
    return { status: response.status, body: result, raw: text, browserUrl: window.location.href };
  }, { requestPath: path, requestMethod: method, payload: body });
}

test("real public/admin routes reject hostile input safely and preserve real database state", async ({ page }) => {
  const live = await page.request.get("/api/health/live");
  expect(live.status()).toBe(200);
  expect(await live.json()).toEqual({ status: "ok" });
  expect(live.headers()["cache-control"]).toBe("no-store");

  const ready = await page.request.get("/api/health/ready");
  expect(ready.status()).toBe(200);
  expect(await ready.json()).toEqual({ status: "ok" });
  expect(ready.headers()["cache-control"]).toBe("no-store");

  const version = await page.request.get("/api/version");
  const versionBody = await version.json() as { commit: string; buildTime: string; environment: string };
  expect(version.status()).toBe(200);
  expect(versionBody.commit).toMatch(/^[a-f0-9]{40}$/);
  expect(versionBody.buildTime).not.toBe("unknown");
  expect(versionBody.environment).toBe("staging");
  expect(JSON.stringify(versionBody)).not.toMatch(/postgres|secret|DATABASE_ADMIN_URL/i);

  const protectedAdmin = await page.request.get("/admin/login");
  const securityHeaders = protectedAdmin.headers();
  expect(securityHeaders["cache-control"]).toContain("no-store");
  expect(securityHeaders["x-content-type-options"]).toBe("nosniff");
  expect(securityHeaders["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  expect(securityHeaders["permissions-policy"]).toContain("geolocation=(self)");
  expect(securityHeaders["permissions-policy"]).toContain("camera=()");
  expect(securityHeaders["permissions-policy"]).toContain("microphone=()");
  expect(securityHeaders["x-frame-options"]).toBe("DENY");
  expect(securityHeaders["content-security-policy-report-only"]).toContain("worker-src 'self' blob:");
  expect(securityHeaders["content-security-policy"]).toBeUndefined();
  expect(securityHeaders["x-robots-tag"]).toContain("noindex, nofollow");
  expect(securityHeaders["strict-transport-security"]).toBeUndefined();
  const robots = await page.request.get("/robots.txt");
  expect(await robots.text()).toContain("Disallow: /");
  const adminSession = await page.request.get("/api/admin/session");
  expect(adminSession.headers()["cache-control"]).toContain("no-store");

  await page.goto("/admin/login");
  const before = await pool.query<{ facilities: string; records: string; candidate_id: string }>(
    `SELECT (SELECT count(*)::text FROM app_private.facilities) AS facilities,
      (SELECT count(*)::text FROM app_private.source_records) AS records,
      (SELECT c.id::text FROM app_private.candidate_records c JOIN app_private.source_records sr ON sr.id=c.source_record_id
       WHERE sr.source_key='clinic-006' ORDER BY sr.collected_at LIMIT 1) AS candidate_id`,
  );
  const beforeState = before.rows[0];

  const publicInputs = [
    "'", '"', "' OR 1=1 --", '"; DROP TABLE facilities; --', "%", "_", "’‘“”", "null",
    "a".repeat(101), "clinic\u0000name",
  ];
  for (const input of publicInputs) {
    const url = `/api/search?q=${encodeURIComponent(input)}&match=prefix`;
    const result = await browserRequest(page, url);
    expect([200, 400]).toContain(result.status);
    expect(JSON.stringify(result.body)).not.toMatch(unsafeLeak);
    if (input.length === 101 || input.includes("\u0000")) expect(result.status).toBe(400);
  }

  const nearbyGet = await browserRequest(page, "/api/nearby?lat=39.123456&lng=116.654321");
  expect(nearbyGet.status).toBe(405);
  const nearbyPath = "/api/nearby";
  const nearbySentinel = await browserRequest(page, nearbyPath, "POST", { lat: 39.123456, lng: 116.654321 });
  expect(nearbySentinel.status).toBe(200);
  expect(nearbySentinel.browserUrl).not.toContain("39.123456");
  expect(nearbySentinel.browserUrl).not.toContain("116.654321");
  expect(nearbyPath).not.toContain("39.123456");
  expect(nearbyPath).not.toContain("116.654321");
  expect(nearbySentinel.raw).not.toContain("39.123456");
  expect(nearbySentinel.raw).not.toContain("116.654321");
  expect(JSON.stringify(nearbySentinel.body)).not.toMatch(unsafeLeak);

  for (const path of [
    "/api/search?q=clinic&region=null",
    "/api/search?q=clinic&category=eye_specialty_hospital%27%20OR%201%3D1",
    "/api/search?q=clinic&cursor=%27%20OR%201%3D1%20--",
    "/api/facilities?bbox=115,39,118,41&zoom=13&region=%27%20OR%201%3D1%20--",
    "/api/facilities?bbox=115,39,118,41&zoom=13&category=unknown%3BDROP%20TABLE%20facilities",
  ]) {
    const response = await browserRequest(page, path);
    expect(response.status).toBe(400);
    expect(JSON.stringify(response.body)).not.toMatch(unsafeLeak);
  }

  await login(page);
  const invalidAdminFilters = [
    "/api/admin/review?type=candidates&limit=20&source=%27%20OR%201%3D1%20--",
    "/api/admin/review?type=candidates&limit=20&region=1%27%20OR%201%3D1",
    "/api/admin/review?type=candidates&limit=20&cursor=%27%20OR%201%3D1",
  ];
  for (const path of invalidAdminFilters) {
    const response = await browserRequest(page, path);
    expect(response.status).toBe(400);
    expect(JSON.stringify(response.body)).not.toMatch(unsafeLeak);
  }

  const malformedIds = [
    `/api/admin/candidates/${encodeURIComponent("' OR 1=1 --")}/decision`,
    `/api/admin/facilities/${encodeURIComponent("'; DROP TABLE facilities; --")}/decision`,
  ];
  for (const path of malformedIds) {
    const response = await browserRequest(page, path, "POST", { action: "PUBLISH", reason: "P13 hostile ID test" });
    expect(response.status).toBe(400);
    expect(JSON.stringify(response.body)).not.toMatch(unsafeLeak);
  }

  const candidateId = beforeState.candidate_id;
  const decisionPath = `/api/admin/candidates/${candidateId}/decision`;
  for (const payload of [
    { action: "CREATE_FACILITY; DROP TABLE facilities; --", reason: "P13 hostile action test" },
    { action: "CREATE_FACILITY", reason: "x".repeat(501) },
    { action: "CREATE_FACILITY", reason: "P13 hostile identifier test", targetFacilityId: "' OR 1=1 --" },
    { action: "CREATE_FACILITY", reason: "P13 oversized field test", name: "x".repeat(2_001) },
  ]) {
    const response = await browserRequest(page, decisionPath, "POST", payload);
    expect(response.status).toBe(400);
    expect(JSON.stringify(response.body)).not.toMatch(unsafeLeak);
  }

  const afterRejected = await pool.query<{ facilities: string; records: string }>(
    "SELECT (SELECT count(*)::text FROM app_private.facilities) AS facilities,(SELECT count(*)::text FROM app_private.source_records) AS records",
  );
  expect(afterRejected.rows[0]).toEqual({ facilities: beforeState.facilities, records: beforeState.records });
  const tables = await pool.query<{ present: boolean }>(
    `SELECT to_regclass('app_private.facilities') IS NOT NULL
      AND to_regclass('app_private.source_records') IS NOT NULL
      AND to_regclass('app_private.candidate_records') IS NOT NULL AS present`,
  );
  expect(tables.rows[0].present).toBe(true);

  const htmlName = '<img src=x onerror="alert(1)"> P13 hostile fixture';
  const hostileAuditReason = "' OR 1=1 -- <svg onload=alert(1)>";
  const created = await browserRequest(page, decisionPath, "POST", {
    action: "CREATE_FACILITY",
    reason: hostileAuditReason,
    name: htmlName,
    address: "北京市朝阳区合成安全测试路1号",
    regionCode: "110105",
    category: "ophthalmology_center",
  });
  expect(created.status, JSON.stringify(created.body)).toBe(200);
  expect(JSON.stringify(created.body)).not.toMatch(unsafeLeak);
  const facilityId = (created.body as { data: { facilityId: string } }).data.facilityId;
  const audit = await pool.query<{ id: string }>(
    "SELECT id FROM app_private.audit_events WHERE entity='candidate' AND entity_id=$1 AND action='CREATE_FACILITY' ORDER BY created_at DESC LIMIT 1",
    [candidateId],
  );

  await page.getByTestId("review-tab-facilities").click();
  const facilityRow = page.getByTestId(`review-row-facilities-${facilityId}`);
  await expect(facilityRow).toBeVisible();
  await facilityRow.click();
  await expect(page.getByRole("heading", { name: htmlName, exact: true })).toBeVisible();
  await expect(page.locator("img, svg[onload]")).toHaveCount(0);

  await page.getByTestId("review-tab-audit").click();
  const auditRow = page.getByTestId(`review-row-audit-${audit.rows[0].id}`);
  await expect(auditRow).toBeVisible();
  await auditRow.click();
  await expect(page.getByRole("region", { name: "审核详情" }).getByText(hostileAuditReason, { exact: true })).toBeVisible();
  await expect(page.locator("img, svg[onload]")).toHaveCount(0);

  const sourceRecordsRemain = await pool.query<{ count: string }>(
    "SELECT count(*)::text AS count FROM app_private.source_records WHERE id IN (SELECT source_record_id FROM app_private.candidate_records WHERE id=$1)",
    [candidateId],
  );
  expect(sourceRecordsRemain.rows[0].count).toBe("1");
});

test.afterAll(async () => { await pool.end(); });
