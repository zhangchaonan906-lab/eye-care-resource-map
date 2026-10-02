import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const REQUIRED_FIELDS = ["status", "owner", "evidence", "requiredAction", "verifiedAt"];
const VALID_STATUSES = new Set(["PASS", "PENDING", "BLOCKED"]);
const VERIFIED_AT_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;

export function validateReleaseGateManifest(manifest) {
  const errors = [];
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) {
    return ["manifest must be an object"];
  }
  if (!manifest.gates || typeof manifest.gates !== "object" || Array.isArray(manifest.gates)) {
    return ["gates must be an object"];
  }

  for (const [name, gate] of Object.entries(manifest.gates)) {
    if (!gate || typeof gate !== "object" || Array.isArray(gate)) {
      errors.push(`${name}: gate must be an object`);
      continue;
    }
    for (const field of REQUIRED_FIELDS) {
      if (!(field in gate)) errors.push(`${name}: missing ${field}`);
    }
    if ("status" in gate && !VALID_STATUSES.has(gate.status)) {
      errors.push(`${name}: status must be PASS, PENDING, or BLOCKED`);
    }
    for (const field of ["owner", "evidence", "requiredAction"]) {
      if (field in gate && (typeof gate[field] !== "string" || gate[field].trim() === "")) {
        errors.push(`${name}: ${field} must be a non-empty string`);
      }
    }
    if ("verifiedAt" in gate && gate.verifiedAt !== null) {
      if (typeof gate.verifiedAt !== "string" || !VERIFIED_AT_PATTERN.test(gate.verifiedAt) || Number.isNaN(Date.parse(gate.verifiedAt))) {
        errors.push(`${name}: verifiedAt must be an ISO-8601 UTC timestamp or null`);
      }
    }
  }
  return errors;
}

export function loadReleaseGateManifest() {
  const path = resolve(import.meta.dirname, "../../docs/operations/p14-release-gates.json");
  const manifest = JSON.parse(readFileSync(path, "utf8"));
  const errors = validateReleaseGateManifest(manifest);
  if (errors.length) throw new Error(`Invalid release gate manifest:\n- ${errors.join("\n- ")}`);
  return manifest;
}
