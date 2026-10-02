import { readFileSync } from "node:fs";
import { resolve } from "node:path";
const gates = JSON.parse(readFileSync(resolve(import.meta.dirname, "../docs/operations/p14-release-gates.json"), "utf8")).gates;
const required = ["SYSTEM_QA", "BUILD", "SECURITY_SCANS", "BACKUP_RESTORE", "STAGING_HEALTH", "STAGING_SMOKE", "STAGING_DATABASE", "STAGING_DEPLOYMENT", "NO_REAL_SOURCE_AUTOMATION"];
const missing = required.filter((name) => gates[name]?.status !== "PASS");
const environmentVariables = ["STAGING_SITE_URL", "PUBLIC_API_DATABASE_URL", "ADMIN_DATABASE_URL", "ADMIN_USERNAME", "ADMIN_PASSWORD_HASH", "ADMIN_SESSION_SECRET", "ADMIN_ACTOR_ID"];
const unconfigured = environmentVariables.filter((name) => !process.env[name]);
if (unconfigured.length) missing.push(`STAGING_ENVIRONMENT_MISSING=${unconfigured.join("/")}`);
if (missing.length) { console.error(`Staging release blocked/pending: ${missing.join(", ")}`); process.exitCode = 1; }
else console.log("Staging release gates passed.");
