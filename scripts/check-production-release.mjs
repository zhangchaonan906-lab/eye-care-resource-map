import { loadReleaseGateManifest } from "./lib/release-gates.mjs";
const gates = loadReleaseGateManifest().gates;
const required = [
  "SYSTEM_QA", "BUILD", "SECURITY_SCANS",
  "STAGING_HEALTH", "STAGING_DATABASE", "STAGING_DEPLOYMENT", "STAGING_SMOKE",
  "NO_REAL_SOURCE_AUTOMATION", "WORKER_HOSTING", "BACKUP_RESTORE",
  "REAL_PUBLISHED_DATA_SAMPLE", "REAL_DATA_QUALITY_SAMPLE", "DATA_CORRECTION_ENTRY",
  "PRODUCTION_BASEMAP", "PRODUCTION_COORDINATE_PROVIDER", "PRODUCTION_SOURCE_COVERAGE",
  "DEPLOYMENT_NEARBY_PRIVACY", "PRODUCTION_SECURITY_HEADERS", "PRODUCTION_RATE_LIMITING", "MONITORING",
];
const blocked = required.filter((name) => gates[name]?.status !== "PASS");
if (blocked.length) { console.error(`Production release blocked: ${blocked.map((name) => `${name}=${gates[name]?.status ?? "MISSING"}`).join(", ")}`); process.exitCode = 1; }
else console.log("Production release gates passed.");
