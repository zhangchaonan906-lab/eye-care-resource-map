import { spawnSync } from "node:child_process";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { existsSync } from "node:fs";
import { resolve, join } from "node:path";

const root = resolve(import.meta.dirname, "..");
const tracked = spawnSync("git", ["ls-files", "-co", "--exclude-standard", "-z"], { cwd: root, encoding: "utf8" });
if (tracked.status !== 0) throw new Error("Could not enumerate repository and Docker context files");
const paths = new Set(tracked.stdout.split("\0").filter(Boolean));
function addTree(directory) {
  if (!statSync(directory, { throwIfNoEntry: false })?.isDirectory()) return;
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (["node_modules", ".git"].includes(entry.name)) continue;
    const absolute = join(directory, entry.name);
    if (entry.isDirectory()) addTree(absolute); else paths.add(absolute.slice(root.length + 1));
  }
}
addTree(resolve(root, "apps/web/.next/static"));
if (existsSync(resolve(root, "release-manifest.json"))) paths.add("release-manifest.json");
const rules = [
  { name: "private key", regex: /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/ },
  { name: "GitHub token", regex: /\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b/ },
  { name: "AWS access key", regex: /\bAKIA[0-9A-Z]{16}\b/ },
  { name: "credential-bearing PostgreSQL URL", regex: /postgres(?:ql)?:\/\/[^\s/:]+:(?!REPLACE_WITH|[$<{])[A-Za-z0-9+/=]{16,}@/i },
];
const findings = [];
for (const item of paths) {
  if (item.includes("node_modules/") || item.includes(".git/") || item.endsWith("package-lock.json")) continue;
  const absolute = resolve(root, item);
  let content;
  try { content = readFileSync(absolute, "utf8"); } catch { continue; }
  for (const rule of rules) if (rule.regex.test(content)) findings.push(`${item}: ${rule.name}`);
}
if (findings.length) { console.error(`Potential secrets found:\n${findings.join("\n")}`); process.exitCode = 1; }
else console.log(`Secret scan passed (${paths.size} repository/Docker-context files plus Web static assets).`);
