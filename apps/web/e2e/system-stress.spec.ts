import { expect, test } from "@playwright/test";

const stressFacilityId = process.env.P13_STRESS_FACILITY_ID!;
const facilityName = "P13 Synthetic Stress Hospital 0001";

test("real map handles 500 visible facilities, clusters them and cancels stale viewport requests", async ({ page }) => {
  const facilityResponses: Array<{ count: number; limit: number; bbox: string; zoom: string }> = [];
  const failedFacilityRequests: string[] = [];
  const facilityApiStatuses: string[] = [];
  let heldRouteReached: () => void = () => {};
  let releaseHeldRoute: () => void = () => {};
  const heldReached = new Promise<void>((resolve) => { heldRouteReached = resolve; });
  const release = new Promise<void>((resolve) => { releaseHeldRoute = resolve; });
  let facilityRequestCount = 0;
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];

  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("requestfailed", (request) => { if (request.url().includes("worker") || request.url().includes("vendor")) failedRequests.push(request.url()); });
  page.on("requestfailed", (request) => {
    if (request.url().includes("/api/facilities?")) failedFacilityRequests.push(request.url());
  });
  page.on("response", async (response) => {
    if (!response.url().includes("/api/facilities?")) return;
    facilityApiStatuses.push(`${response.status()}:${response.url()}`);
    try {
      const payload = await response.json() as { data?: unknown[]; meta?: { limit?: number } };
      const url = new URL(response.url());
      facilityResponses.push({
        count: Array.isArray(payload.data) ? payload.data.length : -1,
        limit: Number(payload.meta?.limit ?? url.searchParams.get("limit")),
        bbox: url.searchParams.get("bbox") ?? "",
        zoom: url.searchParams.get("zoom") ?? "",
      });
    } catch { /* aborted requests have no response body */ }
  });

  await page.goto(`/resources/eye-hospitals?facility=${stressFacilityId}`);
  const map = page.getByTestId("map-canvas");
  await expect(map).toBeVisible();
  const stressRow = page.getByRole("button", { name: new RegExp(facilityName) });
  try {
    await expect(stressRow).toBeVisible({ timeout: 10_000 });
  } catch (error) {
    console.log("P13 stress diagnostics", JSON.stringify({
      facilityApiStatuses,
      currentViewport: await map.getAttribute("data-current-viewport"),
      viewportRevision: await map.getAttribute("data-viewport-revision"),
      clusterFeatureCount: await map.getAttribute("data-cluster-feature-count"),
    }));
    throw error;
  }
  try {
    await expect.poll(async () => Number(await map.getAttribute("data-cluster-feature-count")), { timeout: 20_000 }).toBeGreaterThan(0);
  } catch (error) {
    console.log("P13 cluster diagnostics", JSON.stringify({
      facilityApiStatuses,
      consoleErrors,
      failedRequests,
      canvasCount: await map.locator("canvas").count(),
      viewport: await map.getAttribute("data-current-viewport"),
      clusterFeatureCount: await map.getAttribute("data-cluster-feature-count"),
    }));
    throw error;
  }

  const renderedNames = await page.locator(".eye-map__facility-name").allTextContents();
  expect(renderedNames.filter((name) => name === facilityName)).toHaveLength(1);
  expect(renderedNames.length).toBeGreaterThanOrEqual(500);
  expect(renderedNames.length).toBeLessThanOrEqual(1_200);

  // Let all initial pages settle before intercepting. At 501 total published
  // facilities the API may legitimately paginate, so gating request #2 during
  // startup can strand the initial list in its loading state.
  await page.route("**/api/facilities?*", async (route) => {
    facilityRequestCount += 1;
    if (facilityRequestCount === 1) {
      heldRouteReached();
      await release;
    }
    try { await route.continue(); } catch { /* the browser may cancel this stale viewport request */ }
  });

  const initialRevision = Number(await map.getAttribute("data-viewport-revision"));
  const bounds = await map.boundingBox();
  if (!bounds) throw new Error("Map canvas has no browser bounds");
  await page.mouse.move(bounds.x + bounds.width * 0.32, bounds.y + bounds.height * 0.52);
  await page.mouse.down();
  await page.mouse.move(bounds.x + bounds.width * 0.42, bounds.y + bounds.height * 0.48, { steps: 4 });
  await page.mouse.up();
  await heldReached;
  await page.mouse.move(bounds.x + bounds.width * 0.32, bounds.y + bounds.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(bounds.x + bounds.width * 0.48, bounds.y + bounds.height * 0.54, { steps: 4 });
  await page.mouse.up();
  await expect.poll(async () => Number(await map.getAttribute("data-viewport-revision")), { timeout: 10_000 }).toBeGreaterThan(initialRevision + 1);
  releaseHeldRoute();

  const revisionAfterCancellation = Number(await map.getAttribute("data-viewport-revision"));
  for (let interaction = 0; interaction < 20; interaction += 1) {
    const x = bounds.x + bounds.width * 0.30;
    const y = bounds.y + bounds.height * 0.50;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + (interaction % 2 === 0 ? 45 : -45), y + (interaction % 4 < 2 ? 25 : -25), { steps: 3 });
    await page.mouse.up();
  }
  await page.mouse.move(bounds.x + bounds.width * 0.30, bounds.y + bounds.height * 0.5);
  await page.mouse.wheel(0, -120);
  await page.mouse.wheel(0, 120);
  await page.getByLabel("机构类型").selectOption({ index: 1 });
  await page.getByLabel("机构类型").selectOption("");
  await page.mouse.move(bounds.x + bounds.width * 0.3, bounds.y + bounds.height * 0.5);
  await page.mouse.wheel(0, -35);
  await expect.poll(async () => Number(await map.getAttribute("data-viewport-revision")), { timeout: 10_000 }).toBeGreaterThanOrEqual(revisionAfterCancellation + 15);

  await expect.poll(() => facilityResponses.length, { timeout: 20_000 }).toBeGreaterThanOrEqual(2);
  await expect.poll(() => facilityResponses.length + failedFacilityRequests.length, { timeout: 20_000 }).toBeGreaterThanOrEqual(3);
  expect(failedFacilityRequests.length).toBeGreaterThan(0);
  expect(facilityResponses.every((response) => response.count >= 0 && response.count <= 500 && response.limit <= 500)).toBe(true);
  expect(facilityRequestCount).toBeLessThan(50);
  await expect.poll(async () => {
    const viewport = JSON.parse((await map.getAttribute("data-current-viewport")) ?? "{}") as { bbox?: number[]; zoom?: number };
    return facilityResponses.some((response) => response.bbox === viewport.bbox?.join(",") && Number(response.zoom) === viewport.zoom);
  }, { timeout: 20_000 }).toBe(true);

  await expect(stressRow).toBeVisible();
  await expect.poll(async () => Number(await map.getAttribute("data-cluster-feature-count")), { timeout: 20_000 }).toBeGreaterThan(0);
});
