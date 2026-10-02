import { readFileSync } from "node:fs";
import { resolve } from "node:path";
const gates = JSON.parse(readFileSync(resolve(import.meta.dirname, "../docs/operations/p14-release-gates.json"), "utf8")).gates;
const required = ["SYSTEM_QA", "REAL_PUBLISHED_DATA_SAMPLE", "REAL_DATA_QUALITY_SAMPLE", "PRODUCTION_BASEMAP", "PRODUCTION_COORDINATE_PROVIDER", "PRODUCTION_SOURCE_COVERAGE", "DEPLOYMENT_NEARBY_PRIVACY", "PRODUCTION_SECURITY_HEADERS", "PRODUCTION_RATE_LIMITING", "BACKUP_RESTORE", "MONITORING"];
const blocked = required.filter((name) => gates[name]?.status !== "PASS");
if (blocked.length) { console.error(`Production release blocked: ${blocked.map((name) => `${name}=${gates[name]?.status ?? "MISSING"}`).join(", ")}`); process.exitCode = 1; }
else console.log("Production release gates passed.");
