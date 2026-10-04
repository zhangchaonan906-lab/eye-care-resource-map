import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { pathToFileURL } from "node:url";

const root = resolve(import.meta.dirname, "..");
const webRoot = resolve(root, "apps/web");
const exceptionPath = resolve(root, "docs/security/npm-audit-exceptions.json");
const HIGH_OR_CRITICAL = new Set(["high", "critical"]);
const ALLOWED_ADVISORY_ID = "GHSA-vfj7-8cjw-p6xm";
const MAX_EXCEPTION_AGE_MS = 30 * 24 * 60 * 60 * 1000;

function fail(message) {
  throw new Error(message);
}

function runNpm(args) {
  const windows = process.platform === "win32";
  const command = windows ? "cmd.exe" : "npm";
  const commandArgs = windows ? ["/d", "/s", "/c", `npm ${args.join(" ")}`] : args;
  const result = spawnSync(command, commandArgs, {
    cwd: webRoot,
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
  if (result.error) fail(`Unable to run npm ${args.join(" ")}: ${result.error.message}`);
  return result;
}

function parseJsonOutput(label, result, allowedExitCodes) {
  if (!allowedExitCodes.includes(result.status)) {
    fail(`${label} command exited with status ${result.status}: ${(result.stderr || "").trim()}`);
  }
  try {
    return JSON.parse(result.stdout);
  } catch {
    fail(`${label} command did not return valid JSON`);
  }
}

function severityCount(report, severity) {
  const metadataCount = report?.metadata?.vulnerabilities?.[severity] ?? 0;
  const listedCount = Object.values(report?.vulnerabilities ?? {}).filter(
    (entry) => entry?.severity === severity,
  ).length;
  return Math.max(metadataCount, listedCount);
}

function assertAuditShape(report, label) {
  if (
    !report ||
    typeof report !== "object" ||
    !report.vulnerabilities ||
    typeof report.vulnerabilities !== "object"
  ) {
    fail(`${label} report is malformed`);
  }
  const reportedFindings = severityCount(report, "high") + severityCount(report, "critical");
  const listedFindings = Object.values(report.vulnerabilities).filter(
    (entry) => HIGH_OR_CRITICAL.has(entry?.severity),
  ).length;
  if (reportedFindings > listedFindings) {
    fail(`${label} reports high or critical findings without vulnerability details`);
  }
}

function assertExceptionManifest(manifest, now) {
  if (!manifest || manifest.formatVersion !== 1 || !Array.isArray(manifest.exceptions)) {
    fail("exception manifest formatVersion must be 1 with an exceptions array");
  }
  const seen = new Set();
  for (const exception of manifest.exceptions) {
    const requiredStrings = ["id", "package", "affected", "scope", "reason", "owner", "remediation"];
    if (
      !exception ||
      requiredStrings.some((key) => typeof exception[key] !== "string" || !exception[key].trim())
    ) {
      fail("exception entry is malformed: required string fields are missing");
    }
    if (seen.has(exception.id)) fail(`duplicate exception advisory ${exception.id}`);
    seen.add(exception.id);
    if (exception.id !== ALLOWED_ADVISORY_ID) fail(`unsupported advisory exception ${exception.id}`);
    if (exception.scope !== "dev-only") fail(`unsupported exception scope for ${exception.id}`);
    const approvedAt = Date.parse(exception.approvedAt);
    const expiresAt = Date.parse(exception.expiresAt);
    if (!Number.isFinite(approvedAt) || !Number.isFinite(expiresAt)) {
      fail(`exception ${exception.id} has invalid approval or expiry timestamp`);
    }
    if (approvedAt > now) fail(`exception ${exception.id} approval is in the future`);
    if (expiresAt <= now) fail(`exception ${exception.id} expired`);
    if (expiresAt <= approvedAt || expiresAt - approvedAt > MAX_EXCEPTION_AGE_MS) {
      fail(`exception ${exception.id} must expire within 30 days of approval`);
    }
  }
  return manifest.exceptions;
}

function collectRootAdvisories(packageName, audit, visited = new Set()) {
  if (visited.has(packageName)) return [];
  visited.add(packageName);
  const vulnerability = audit.vulnerabilities[packageName];
  if (!vulnerability) return [];
  const roots = [];
  for (const via of vulnerability.via ?? []) {
    if (typeof via === "string") {
      roots.push(...collectRootAdvisories(via, audit, visited));
    } else if (via && typeof via === "object" && typeof via.source === "string") {
      roots.push({
        id: via.source,
        package: typeof via.name === "string" ? via.name : packageName,
        range: typeof via.range === "string" ? via.range : "",
        severity: via.severity,
      });
    } else if (via && typeof via === "object" && typeof via.url === "string") {
      const advisoryId = via.url.match(/GHSA-[A-Za-z0-9-]+/)?.[0];
      if (advisoryId) {
        roots.push({
          id: advisoryId,
          package: typeof via.name === "string" ? via.name : packageName,
          range: typeof via.range === "string" ? via.range : "",
          severity: via.severity,
        });
      }
    }
  }
  return roots;
}

function compareVersions(left, right) {
  const parse = (version) => {
    const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(version);
    if (!match) fail(`unsupported semantic version in audit exception validation: ${version}`);
    return match.slice(1).map(Number);
  };
  const a = parse(left);
  const b = parse(right);
  for (let index = 0; index < 3; index += 1) {
    if (a[index] !== b[index]) return a[index] < b[index] ? -1 : 1;
  }
  return 0;
}

function versionMatchesRange(version, range) {
  const match = /^(<=|>=|<|>|=)?\s*(\d+\.\d+\.\d+)$/.exec(range);
  if (!match) fail(`unsupported affected range in audit exception: ${range}`);
  const comparison = compareVersions(version, match[2]);
  switch (match[1] ?? "=") {
    case "<=": return comparison <= 0;
    case ">=": return comparison >= 0;
    case "<": return comparison < 0;
    case ">": return comparison > 0;
    case "=": return comparison === 0;
    default: return false;
  }
}

function findPackageLockNodes(packageLock, packageName, nodePaths) {
  const packages = packageLock?.packages;
  if (!packages || typeof packages !== "object") fail("package-lock packages map is missing");
  const paths = nodePaths.length
    ? nodePaths
    : Object.keys(packages).filter(
      (path) => path === `node_modules/${packageName}` || path.endsWith(`/node_modules/${packageName}`),
    );
  if (paths.length === 0) fail(`exception package ${packageName} is missing from package-lock`);
  return paths.map((path) => {
    const entry = packages[path];
    if (!entry) fail(`package-lock node is missing for ${path}`);
    if (entry.dev !== true) fail(`package-lock does not mark braces as dev-only at ${path}`);
    return { path, entry };
  });
}

function findRuntimePackages(tree, packageName, currentPath = "", found = []) {
  if (!tree || typeof tree !== "object") return found;
  for (const [name, entry] of Object.entries(tree.dependencies ?? {})) {
    const nextPath = currentPath ? `${currentPath} > ${name}` : name;
    if (name === packageName || entry?.name === packageName) found.push(nextPath);
    findRuntimePackages(entry, packageName, nextPath, found);
  }
  return found;
}

export function evaluateAuditPolicy({
  fullAudit,
  runtimeAudit,
  packageLock,
  runtimeTree,
  exceptionManifest,
  now = Date.now(),
}) {
  assertAuditShape(fullAudit, "full npm audit");
  assertAuditShape(runtimeAudit, "runtime npm audit");
  if (
    !runtimeTree ||
    typeof runtimeTree !== "object" ||
    !runtimeTree.dependencies ||
    typeof runtimeTree.dependencies !== "object"
  ) {
    fail("production npm dependency tree is malformed");
  }
  const currentTime = typeof now === "string" ? Date.parse(now) : now;
  if (!Number.isFinite(currentTime)) fail("audit evaluation time is invalid");
  const exceptions = assertExceptionManifest(exceptionManifest, currentTime);
  if (severityCount(runtimeAudit, "high") > 0 || severityCount(runtimeAudit, "critical") > 0) {
    fail("runtime audit contains high or critical vulnerabilities");
  }

  const highFindings = Object.entries(fullAudit.vulnerabilities).filter(([, entry]) =>
    HIGH_OR_CRITICAL.has(entry?.severity),
  );
  for (const [findingName, finding] of highFindings) {
    const fix = finding.fixAvailable;
    if (fix === true || (fix && typeof fix === "object" && fix.isSemVerMajor !== true)) {
      fail(`PATCH_REVIEW_REQUIRED: npm audit reports a non-breaking fix path for ${findingName}`);
    }
  }
  const usedExceptionIds = new Set();
  let exceptionDetails = null;

  for (const [findingName] of highFindings) {
    const roots = collectRootAdvisories(findingName, fullAudit);
    if (roots.length === 0) fail(`cannot resolve root advisory for high or critical finding ${findingName}`);
    for (const rootAdvisory of roots) {
      const exception = exceptions.find((candidate) => candidate.id === rootAdvisory.id);
      if (!exception) fail(`unapproved high or critical advisory ${rootAdvisory.id}`);
      if (exception.package !== rootAdvisory.package) {
        fail(`exception ${exception.id} does not match affected package ${rootAdvisory.package}`);
      }
      if (exception.affected !== rootAdvisory.range) {
        fail(`exception ${exception.id} affected range does not match npm audit metadata`);
      }
      const rootVulnerability = fullAudit.vulnerabilities[rootAdvisory.package];
      const nodes = findPackageLockNodes(packageLock, exception.package, rootVulnerability?.nodes ?? []);
      for (const { entry } of nodes) {
        if (!versionMatchesRange(entry.version, exception.affected)) {
          fail(`PATCH_REVIEW_REQUIRED: ${exception.package}@${entry.version} is outside ${exception.affected}`);
        }
      }
      const runtimeMatches = findRuntimePackages(runtimeTree, exception.package);
      if (runtimeMatches.length > 0) {
        fail(`BRACES_RUNTIME_EXPOSURE = YES (${runtimeMatches.join(", ")})`);
      }
      usedExceptionIds.add(exception.id);
      exceptionDetails = {
        id: exception.id,
        package: exception.package,
        version: nodes[0].entry.version,
        expiresAt: exception.expiresAt,
      };
    }
  }

  const unused = exceptions.filter((exception) => !usedExceptionIds.has(exception.id));
  if (unused.length > 0) {
    fail(`PATCH_REVIEW_REQUIRED: approved advisory no longer appears in npm audit: ${unused.map((item) => item.id).join(", ")}`);
  }

  const status = highFindings.length === 0 ? "PASS" : "KNOWN_DEV_EXCEPTION";
  return {
    runtimeAuditStatus: "PASS",
    fullAuditStatus: status,
    runtimeExposure: "NO",
    exception: exceptionDetails,
  };
}

function readJson(path, label) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    fail(`${label} could not be read as JSON: ${error.message}`);
  }
}

function main() {
  const fullAudit = parseJsonOutput("npm audit --json", runNpm(["audit", "--json"]), [0, 1]);
  const runtimeAudit = parseJsonOutput(
    "npm audit --omit=dev --json",
    runNpm(["audit", "--omit=dev", "--json"]),
    [0, 1],
  );
  const runtimeTree = parseJsonOutput(
    "npm ls --omit=dev --all --json",
    runNpm(["ls", "--omit=dev", "--all", "--json"]),
    [0],
  );
  const result = evaluateAuditPolicy({
    fullAudit,
    runtimeAudit,
    packageLock: readJson(resolve(webRoot, "package-lock.json"), "package-lock"),
    runtimeTree,
    exceptionManifest: readJson(exceptionPath, "npm audit exception manifest"),
  });

  console.log("Runtime npm audit: PASS");
  console.log(`Full npm audit: ${result.fullAuditStatus}`);
  if (result.exception) {
    console.log(`Exception: ${result.exception.id}`);
    console.log(`Package: ${result.exception.package}@${result.exception.version}`);
    console.log(`Runtime exposure: ${result.runtimeExposure}`);
    console.log(`Expires: ${result.exception.expiresAt}`);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    main();
  } catch (error) {
    console.error(`npm dependency audit failed closed: ${error.message}`);
    process.exitCode = 1;
  }
}
