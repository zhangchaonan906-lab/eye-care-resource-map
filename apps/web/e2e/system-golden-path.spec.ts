import { expect, test, type Page } from "@playwright/test";
import { Pool } from "pg";
import { spawn } from "node:child_process";

const facilityName = "样例综合医院（东院）";
const facilityAddress = "北京市朝阳区样例路1号";
const candidateId = process.env.P13_CANDIDATE_ID!;
const duplicateCaseId = process.env.P13_DUPLICATE_CASE_ID!;
const locationId = process.env.P13_LOCATION_ID!;
const adminDb = new Pool({ connectionString: process.env.DATABASE_ADMIN_URL, max: 3 });

function runCollector(args: string[]): Promise<{ status: number; stdout: string; stderr: string }> {
  const command = process.platform === "win32" ? "py" : "python3";
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd: "../../services/collector", env: process.env, windowsHide: true });
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8").on("data", (chunk: string) => { stdout += chunk; });
    child.stderr.setEncoding("utf8").on("data", (chunk: string) => { stderr += chunk; });
    child.once("error", reject);
    child.once("close", (status) => resolve({ status: status ?? -1, stdout, stderr }));
  });
}

async function login(page: Page) {
  await page.goto("/admin/login");
  const csrfCookieCheck = await page.evaluate(async () => {
    const response = await fetch("/api/admin/session", { cache: "no-store" });
    const result = await response.json() as { data?: { csrfToken?: string } };
    const rawCookie = document.cookie.split("; ").find((part) => part.startsWith("eye_admin_pre_csrf="))?.slice("eye_admin_pre_csrf=".length);
    return Boolean(rawCookie && decodeURIComponent(rawCookie) === result.data?.csrfToken);
  });
  if (!csrfCookieCheck) throw new Error("Browser did not retain the matching pre-login CSRF cookie");
  await page.getByLabel("用户名").fill(process.env.ADMIN_USERNAME!);
  await page.getByLabel("密码").fill(process.env.P13_ADMIN_PASSWORD!);
  const loginResponsePromise = page.waitForResponse((response) =>
    response.url().endsWith("/api/admin/session") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "登录审核台" }).click();
  const loginResponse = await loginResponsePromise;
  if (!loginResponse.ok()) {
    const headers = await loginResponse.request().allHeaders();
    const body = await loginResponse.json() as { error?: { code?: string; message?: string } };
    throw new Error(`Admin login rejected (${loginResponse.status()} ${body.error?.code ?? "unknown"}: ${body.error?.message ?? "no message"}; origin=${headers.origin ?? "missing"}; csrf_header=${Boolean(headers["x-csrf-token"])}; prelogin_cookie=${headers.cookie?.includes("eye_admin_pre_csrf=") ?? false})`);
  }
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: "审核控制台" })).toBeVisible();
}

async function selectQueueRow(page: Page, queue: string, id: string) {
  const tab = page.getByTestId(`review-tab-${queue}`);
  if (!(await tab.getAttribute("class"))?.includes("is-active")) {
    const loaded = page.waitForResponse((response) =>
      response.url().includes(`/api/admin/review?type=${queue}`) && response.request().method() === "GET",
    );
    await tab.click();
    const response = await loaded;
    if (!response.ok()) throw new Error(`${queue} review queue returned ${response.status()}: ${JSON.stringify(await response.json())}`);
  }
  const row = page.getByTestId(`review-row-${queue}-${id}`);
  await expect(row).toBeVisible();
  await row.click();
}

async function reason(page: Page, text: string) {
  await page.getByLabel(/操作理由/).fill(text);
}

async function clickAction(page: Page, name: string, why: string) {
  await reason(page, why);
  await page.getByRole("button", { name, exact: true }).click();
  await expect(page.locator(".admin-status")).toContainText("操作已完成");
}

async function csrfToken(page: Page): Promise<string> {
  return page.evaluate(async () => {
    const response = await fetch("/api/admin/session", { cache: "no-store" });
    const result = await response.json();
    return result.data.csrfToken as string;
  });
}

async function publishDecision(page: Page, id: string, token: string) {
  return page.evaluate(async ({ facilityId, csrf }) => {
    const response = await fetch(`/api/admin/facilities/${facilityId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf, "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({ action: "PUBLISH", reason: "P13 pending duplicate gate validation" }),
    });
    return { status: response.status, body: await response.json() };
  }, { facilityId: id, csrf: token });
}

async function queryPublic(page: Page, pathname: string) {
  return page.evaluate(async (path) => {
    const response = await fetch(path, { cache: "no-store" });
    return { status: response.status, body: await response.json() };
  }, pathname);
}

async function pagedFacilityPresence(page: Page, id: string): Promise<boolean> {
  let cursor: string | undefined;
  for (let pageIndex = 0; pageIndex < 4; pageIndex += 1) {
    const params = new URLSearchParams({ bbox: "116.3,39.8,116.5,40.0", zoom: "13", limit: "500" });
    if (cursor) params.set("cursor", cursor);
    const result = await queryPublic(page, `/api/facilities?${params.toString()}`);
    if (result.status !== 200) throw new Error(`facility list failed with ${result.status}`);
    const rows = result.body.data as Array<{ id: string }>;
    if (rows.some((row) => row.id === id)) return true;
    cursor = (result.body.meta?.nextCursor as string | null) ?? undefined;
    if (!cursor) return false;
  }
  throw new Error("facility list cursor did not terminate within four pages");
}

async function visibleInAllPublicSurfaces(page: Page, id: string): Promise<boolean> {
  const [search, nearby, detail, list] = await Promise.all([
    queryPublic(page, `/api/search?q=${encodeURIComponent(facilityName)}&match=exact&limit=20`),
    queryPublic(page, "/api/nearby?lat=39.908&lng=116.397&radius=10000&limit=100"),
    queryPublic(page, `/api/facilities/${id}`),
    pagedFacilityPresence(page, id),
  ]);
  const resultRows = [search, nearby].flatMap((result) => Array.isArray(result.body.data) ? result.body.data : []);
  return list || detail.status === 200 || resultRows.some((row) => row.id === id);
}

test.describe("P13 system golden path: disposable PostGIS, real routes and real review UI", () => {
  test("collector through review, publish, return, republish and withdraw; incremental changes never alter published values", async ({ page }) => {
    page.on("dialog", (dialog) => void dialog.accept());
    await login(page);

    await selectQueueRow(page, "candidates", candidateId);
    await page.getByText("建立审核中机构", { exact: true }).click();
    await page.locator("#candidate-name").fill(facilityName);
    await page.locator("#candidate-address").fill(facilityAddress);
    await page.locator("#candidate-region").fill("110105");
    await page.getByLabel("机构类别").selectOption("general_hospital_ophthalmology");
    await clickAction(page, "建立并进入审核", "P13 synthetic real browser to database path");

    const facilityRows = await adminDb.query<{ id: string }>(
      "SELECT id FROM app_private.facilities WHERE name=$1 AND address=$2 ORDER BY created_at DESC LIMIT 1",
      [facilityName, facilityAddress],
    );
    const facilityId = facilityRows.rows[0]?.id;
    expect(facilityId).toMatch(/^[0-9a-f-]{36}$/i);

    await selectQueueRow(page, "locations", locationId);
    await clickAction(page, "核验坐标", "P13 synthetic coordinates passed region review");
    await selectQueueRow(page, "locations", locationId);
    await clickAction(page, "提升为机构位置", "P13 synthetic location promotion");
    const promoted = await adminDb.query<{ status: string }>(
      "SELECT location_status AS status FROM app_private.facility_locations WHERE facility_id=$1",
      [facilityId],
    );
    expect(promoted.rows[0]?.status).toBe("verified");

    await selectQueueRow(page, "facilities", facilityId!);
    await clickAction(page, "核验机构", "P13 source evidence and synthetic location verified");
    await selectQueueRow(page, "facilities", facilityId!);
    const publishButton = page.getByRole("button", { name: "发布", exact: true });
    await expect(publishButton).toBeDisabled();
    const token = await csrfToken(page);
    const blocked = await publishDecision(page, facilityId!, token);
    expect(blocked.status).toBe(409);
    expect(blocked.body.error.code).toBe("ACTION_BLOCKED");
    expect(blocked.body.error.message).toContain("PENDING_DUPLICATE_REVIEW");

    await selectQueueRow(page, "duplicates", duplicateCaseId);
    await page.locator("summary").filter({ hasText: "合并候选" }).click();
    await page.locator("#duplicate-target").fill(facilityId!);
    await clickAction(page, "合并候选", "P13 duplicate case merged through reviewer UI");
    const merged = await adminDb.query<{ count: string; linked: string }>(
      `SELECT count(*)::text AS candidate_count,
         count(*) FILTER (WHERE proposed_facility_id=$2)::text AS linked_count
       FROM app_private.duplicate_case_candidates m
       JOIN app_private.candidate_records c ON c.id=m.candidate_record_id
       WHERE m.duplicate_case_id=$1`, [duplicateCaseId, facilityId],
    );
    expect(merged.rows[0]).toEqual({ candidate_count: "2", linked_count: "2" });

    await selectQueueRow(page, "duplicates", duplicateCaseId);
    await clickAction(page, "重新打开冲突", "P13 duplicate rollback reviewed through UI");
    const reopened = await adminDb.query<{ resolution: string; audit_count: string; source_count: string }>(
      `SELECT d.resolution,
        (SELECT count(*)::text FROM app_private.audit_events WHERE entity='duplicate' AND entity_id=d.id AND action='REOPEN_DUPLICATE_CASE') AS audit_count,
        (SELECT count(*)::text FROM app_private.source_records sr JOIN app_private.candidate_records c ON c.source_record_id=sr.id JOIN app_private.duplicate_case_candidates m ON m.candidate_record_id=c.id WHERE m.duplicate_case_id=d.id) AS source_count
       FROM app_private.duplicate_cases d WHERE d.id=$1`, [duplicateCaseId],
    );
    expect(reopened.rows[0]).toEqual({ resolution: "pending", audit_count: "1", source_count: "2" });
    await selectQueueRow(page, "duplicates", duplicateCaseId);
    await clickAction(page, "拆分为不同机构", "P13 synthetic candidates reviewed as separate facilities");
    expect((await adminDb.query("SELECT resolution FROM app_private.duplicate_cases WHERE id=$1", [duplicateCaseId])).rows[0].resolution).toBe("separate");

    await selectQueueRow(page, "facilities", facilityId!);
    await clickAction(page, "发布", "P13 synthetic facility publication after duplicate review");
    const original = await adminDb.query<{ name: string; address: string; longitude: number; latitude: number }>(
      `SELECT f.name,f.address,ST_X(l.geog_wgs84::geometry) AS longitude,ST_Y(l.geog_wgs84::geometry) AS latitude
       FROM app_private.facilities f JOIN app_private.facility_locations l ON l.facility_id=f.id WHERE f.id=$1`, [facilityId],
    );
    expect(original.rows[0]).toMatchObject({ name: facilityName, address: facilityAddress });

    await adminDb.query("UPDATE app_private.source_sync_policies SET next_due_at=now()-interval '1 minute' WHERE adapter_key='fixture' AND region_code='110000'");
    const scheduler = await runCollector(["-m", "eye_collector.cli", "scheduler", "--once"]);
    expect(scheduler.status, scheduler.stderr).toBe(0);
    expect(scheduler.stdout).toContain('"queued":1');
    const updatedWorker = await runCollector(["tests/system/run_updated_fixture_worker.py"]);
    expect(updatedWorker.status, `${updatedWorker.stderr}\n${updatedWorker.stdout}`).toBe(0);

    const change = await adminDb.query<{ change_type: string; previous_source_record_id: string; paths: string[]; old_snapshot_count: string }>(
      `SELECT event.change_type,event.previous_source_record_id,event.changed_paths AS paths,
        (SELECT count(*)::text FROM app_private.source_records old WHERE old.id=event.previous_source_record_id) AS old_snapshot_count
       FROM app_private.source_change_events event WHERE event.source_key='clinic-002' AND event.change_type='CHANGED'
       ORDER BY event.created_at DESC LIMIT 1`,
    );
    expect(change.rows[0]?.change_type, `worker=${updatedWorker.stdout}; task state=${JSON.stringify((await adminDb.query(
      "SELECT status,last_error_code,last_error_summary FROM app_private.source_sync_tasks WHERE adapter_key='fixture' AND region_code='110000' ORDER BY created_at DESC LIMIT 3",
    )).rows)}`).toBe("CHANGED");
    expect(change.rows[0]?.previous_source_record_id).toBeTruthy();
    expect(change.rows[0]?.paths).toEqual(expect.arrayContaining(["name", "updated_at"]));
    expect(change.rows[0]?.old_snapshot_count).toBe("1");
    const afterUpdate = await adminDb.query<{ name: string; address: string; longitude: number; latitude: number }>(
      `SELECT f.name,f.address,ST_X(l.geog_wgs84::geometry) AS longitude,ST_Y(l.geog_wgs84::geometry) AS latitude
       FROM app_private.facilities f JOIN app_private.facility_locations l ON l.facility_id=f.id WHERE f.id=$1`, [facilityId],
    );
    expect(afterUpdate.rows[0]).toEqual(original.rows[0]);

    const published = await visibleInAllPublicSurfaces(page, facilityId!);
    expect(published).toBe(true);
    await page.goto("/resources/eye-hospitals");
    const search = page.getByRole("searchbox", { name: "搜索医院" });
    await search.fill("样例综合医院");
    await expect(page.getByRole("button", { name: new RegExp(facilityName) })).toBeVisible();
    await page.getByRole("button", { name: new RegExp(facilityName) }).click();
    await expect(page.getByRole("dialog")).toContainText(facilityAddress);
    await page.goto(`/hospitals/${facilityId}`);
    await expect(page.getByRole("heading", { name: facilityName })).toBeVisible();

    await page.goto("/admin");
    await expect(page.getByRole("heading", { name: "审核控制台" })).toBeVisible();
    await selectQueueRow(page, "facilities", facilityId!);
    await clickAction(page, "退回审核", "P13 return removes all public surfaces");
    expect(await visibleInAllPublicSurfaces(page, facilityId!)).toBe(false);
    const returnedPage = await page.goto(`/hospitals/${facilityId}`);
    expect(returnedPage?.status()).toBe(404);

    await page.goto("/admin");
    await expect(page.getByRole("heading", { name: "审核控制台" })).toBeVisible();
    await selectQueueRow(page, "facilities", facilityId!);
    await clickAction(page, "核验机构", "P13 facility reverified after return");
    await selectQueueRow(page, "facilities", facilityId!);
    await clickAction(page, "发布", "P13 facility republished after re-verification");
    expect(await visibleInAllPublicSurfaces(page, facilityId!)).toBe(true);

    await selectQueueRow(page, "facilities", facilityId!);
    await clickAction(page, "撤回发布", "P13 explicit synthetic facility withdrawal");
    expect(await visibleInAllPublicSurfaces(page, facilityId!)).toBe(false);
    const finalState = await adminDb.query<{ status: string; source_records: string; actions: string[] }>(
      `SELECT f.verification_status AS status,
        (SELECT count(*)::text FROM app_private.source_records sr JOIN app_private.source_catalog sc ON sc.id=sr.source_id WHERE sc.name='Fixture Directory') AS source_records,
        (SELECT array_agg(action ORDER BY created_at) FROM app_private.audit_events WHERE entity_id=$1 AND action IN ('PUBLISH','RETURN_TO_REVIEW','WITHDRAW')) AS actions
       FROM app_private.facilities f WHERE f.id=$1`, [facilityId],
    );
    expect(finalState.rows[0]?.status).toBe("withdrawn");
    expect(Number(finalState.rows[0]?.source_records)).toBeGreaterThan(0);
    expect(finalState.rows[0]?.actions).toEqual(["PUBLISH", "RETURN_TO_REVIEW", "PUBLISH", "WITHDRAW"]);
  });
});

test.afterAll(async () => { await adminDb.end(); });
