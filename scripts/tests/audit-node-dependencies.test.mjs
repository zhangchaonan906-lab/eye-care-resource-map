import test from "node:test";
import assert from "node:assert/strict";
import { evaluateAuditPolicy } from "../audit-node-dependencies.mjs";

const ADVISORY = "GHSA-vfj7-8cjw-p6xm";
const NOW = "2026-10-05T00:00:00.000Z";
const EMPTY_AUDIT = {
  vulnerabilities: {},
  metadata: { vulnerabilities: { high: 0, critical: 0 } },
};
const EMPTY_LOCK = { packages: {} };
const EMPTY_RUNTIME_TREE = { name: "web", dependencies: {} };

function advisory(id = ADVISORY, packageName = "braces", range = "<=3.0.3") {
  return {
    source: 1240992,
    url: `https://github.com/advisories/${id}`,
    name: packageName,
    severity: "high",
    range,
  };
}

function auditWithBraces(id = ADVISORY, packageName = "braces") {
  return {
    vulnerabilities: {
      braces: {
        name: "braces",
        severity: "high",
        via: [advisory(id, packageName)],
        nodes: ["node_modules/braces"],
      },
      micromatch: {
        name: "micromatch",
        severity: "high",
        via: ["braces"],
        nodes: ["node_modules/micromatch"],
      },
      "fast-glob": {
        name: "fast-glob",
        severity: "high",
        via: ["micromatch"],
        nodes: ["node_modules/fast-glob"],
      },
      "@next/eslint-plugin-next": {
        name: "@next/eslint-plugin-next",
        severity: "high",
        via: ["fast-glob"],
        nodes: ["node_modules/@next/eslint-plugin-next"],
      },
      "eslint-config-next": {
        name: "eslint-config-next",
        severity: "high",
        via: ["@next/eslint-plugin-next"],
        nodes: ["node_modules/eslint-config-next"],
      },
    },
    metadata: { vulnerabilities: { high: 5, critical: 0 } },
  };
}

function manifest(overrides = {}) {
  return {
    formatVersion: 1,
    exceptions: [
      {
        id: ADVISORY,
        package: "braces",
        affected: "<=3.0.3",
        scope: "dev-only",
        reason: "Unpatched transitive development dependency.",
        owner: "project-maintainer",
        approvedAt: "2026-10-05T00:00:00.000Z",
        expiresAt: "2026-11-04T00:00:00.000Z",
        remediation: "Remove the exception when a compatible upstream patch is available.",
        ...overrides,
      },
    ],
  };
}

function lockWithBraces(dev = true) {
  return {
    packages: {
      "node_modules/braces": { version: "3.0.3", dev },
    },
  };
}

function evaluate(overrides = {}) {
  return evaluateAuditPolicy({
    fullAudit: EMPTY_AUDIT,
    runtimeAudit: EMPTY_AUDIT,
    packageLock: EMPTY_LOCK,
    runtimeTree: EMPTY_RUNTIME_TREE,
    exceptionManifest: { formatVersion: 1, exceptions: [] },
    now: NOW,
    ...overrides,
  });
}

test("no vulnerabilities pass without exceptions", () => {
  assert.equal(evaluate().fullAuditStatus, "PASS");
  assert.equal(evaluate().runtimeAuditStatus, "PASS");
});

test("a runtime high finding fails even when its package is excepted", () => {
  assert.throws(
    () => evaluate({ runtimeAudit: auditWithBraces() }),
    /runtime audit contains high or critical vulnerabilities/,
  );
});

test("a production dependency tree containing the excepted package fails", () => {
  assert.throws(
    () => evaluate({
      fullAudit: auditWithBraces(),
      packageLock: lockWithBraces(),
      exceptionManifest: manifest(),
      runtimeTree: { name: "web", dependencies: { braces: { version: "3.0.3" } } },
    }),
    /BRACES_RUNTIME_EXPOSURE = YES/,
  );
});

test("an unknown development high advisory fails closed", () => {
  assert.throws(
    () => evaluate({ fullAudit: auditWithBraces("GHSA-unknown", "braces") }),
    /unapproved high or critical advisory GHSA-unknown/,
  );
});

test("an exact allowlisted development advisory passes with runtime absent", () => {
  const result = evaluate({
    fullAudit: auditWithBraces(),
    packageLock: lockWithBraces(),
    exceptionManifest: manifest(),
  });
  assert.equal(result.fullAuditStatus, "KNOWN_DEV_EXCEPTION");
  assert.equal(result.exception.id, ADVISORY);
  assert.equal(result.runtimeExposure, "NO");
});

test("an expired exception fails", () => {
  assert.throws(
    () => evaluate({
      fullAudit: auditWithBraces(),
      packageLock: lockWithBraces(),
      exceptionManifest: manifest({ expiresAt: "2026-10-04T23:59:59.000Z" }),
    }),
    /exception GHSA-vfj7-8cjw-p6xm expired/,
  );
});

test("an exception for the wrong package fails", () => {
  assert.throws(
    () => evaluate({
      fullAudit: auditWithBraces(),
      packageLock: lockWithBraces(),
      exceptionManifest: manifest({ package: "micromatch" }),
    }),
    /does not match affected package braces/,
  );
});

test("a second advisory on the same package is not covered by the exception", () => {
  const audit = auditWithBraces();
  audit.vulnerabilities.braces.via.push(advisory("GHSA-another", "braces"));
  assert.throws(
    () => evaluate({
      fullAudit: audit,
      packageLock: lockWithBraces(),
      exceptionManifest: manifest(),
    }),
    /unapproved high or critical advisory GHSA-another/,
  );
});

test("a dev-only claim fails when the lockfile marks braces as runtime", () => {
  assert.throws(
    () => evaluate({
      fullAudit: auditWithBraces(),
      packageLock: lockWithBraces(false),
      exceptionManifest: manifest(),
    }),
    /package-lock does not mark braces as dev-only/,
  );
});

test("a malformed exception manifest fails", () => {
  assert.throws(
    () => evaluate({ exceptionManifest: { formatVersion: 2, exceptions: [] } }),
    /exception manifest formatVersion must be 1/,
  );
});

test("an unused exception requires patch review", () => {
  assert.throws(
    () => evaluate({ exceptionManifest: manifest() }),
    /PATCH_REVIEW_REQUIRED/,
  );
});

test("a non-breaking upstream fix path requires patch review", () => {
  const audit = auditWithBraces();
  audit.vulnerabilities.braces.fixAvailable = { version: "3.0.4", isSemVerMajor: false };
  assert.throws(
    () => evaluate({
      fullAudit: audit,
      packageLock: lockWithBraces(),
      exceptionManifest: manifest(),
    }),
    /PATCH_REVIEW_REQUIRED: npm audit reports a non-breaking fix path/,
  );
});
