const base = process.env.STAGING_SITE_URL ?? process.argv.find((arg) => arg.startsWith("--base-url="))?.slice(11);
if (!base) { console.error("STAGING_SMOKE=PENDING_CREDENTIALS: set STAGING_SITE_URL (or --base-url for local disposable smoke). No deployment attempted."); process.exit(2); }
const origin = new URL(base);
if (origin.username || origin.password || origin.search || origin.hash) throw new Error("Smoke URL must not contain credentials, query, or fragment");
let checks = 0;
async function check(path, accept, init) {
  const response = await fetch(new URL(path, origin), { redirect: "manual", ...init });
  if (!accept(response)) throw new Error(`Smoke check failed for ${path}: HTTP ${response.status}`);
  checks += 1; return response;
}
await check("/api/health/live", (r) => r.status === 200);
await check("/api/health/ready", (r) => r.status === 200);
const search = await check("/api/search?q=P14-SMOKE-NO-RESULT", (r) => r.status === 200);
const searchPayload = await search.json();
if (!Array.isArray(searchPayload.data) || searchPayload.data.length !== 0) throw new Error("Synthetic staging search did not return the expected empty state");
const mapPage = await check("/resources/eye-hospitals", (r) => r.status === 200);
if (!mapPage.headers.get("x-robots-tag")?.includes("noindex")) throw new Error("Staging map response is missing noindex");
const adminLogin = await check("/admin/login", (r) => r.status === 200);
if (!adminLogin.headers.get("cache-control")?.includes("no-store")) throw new Error("Admin login response is cacheable");
await check("/api/facilities/00000000-0000-4000-8000-000000000000", (r) => r.status === 404);
await check("/api/nearby", (r) => r.status === 405);
const nearby = await check("/api/nearby", (r) => r.status === 400, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ lat: 39.123456, lng: 116.654321, radius: -1 }) });
if (nearby.url.includes("39.123456") || nearby.url.includes("116.654321")) throw new Error("Nearby coordinates leaked into request URL");
const security = await check("/api/health/live", (r) => r.headers.get("x-content-type-options") === "nosniff");
if (origin.protocol === "https:" && !security.headers.has("strict-transport-security")) throw new Error("HTTPS smoke target is missing HSTS");
for (const key of ["referrer-policy", "permissions-policy", "content-security-policy-report-only"]) if (!security.headers.has(key)) throw new Error(`Security header missing: ${key}`);
const robots = await check("/robots.txt", (r) => r.status === 200);
if (!(await robots.text()).includes("Disallow: /")) throw new Error("Staging robots.txt does not disallow indexing");
const version = await fetch(new URL("/api/version", origin), { cache: "no-store" }).then((r) => r.json());
if (typeof version.commit !== "string" || version.environment !== "staging") throw new Error("Version endpoint does not identify the staging release");
console.log(`Staging smoke PASS (${checks} checks); commit=${version.commit}; environment=${version.environment}`);
