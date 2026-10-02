import { scryptSync } from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ADMIN_CSRF_COOKIE,
  ADMIN_SESSION_COOKIE,
  createAdminSessionToken,
  cookieOptions,
  isSameOrigin,
  readAdminSession,
  verifyCsrf,
  verifyPasswordHash,
} from "./auth";

const secret = "test-session-secret-with-more-than-32-characters";
const actorId = "00000000-0000-4000-8000-000000000001";

function passwordHash(password: string, salt = "0123456789abcdef") {
  const digest = scryptSync(password, salt, 64, { N: 16384, r: 8, p: 1, maxmem: 64 * 1024 * 1024 });
  return `scrypt$16384$8$1$${Buffer.from(salt).toString("base64url")}$${digest.toString("base64url")}`;
}

describe("admin authentication boundary", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("verifies only a scrypt password hash and rejects malformed hash configuration", async () => {
    const hash = passwordHash("correct horse");
    await expect(verifyPasswordHash("correct horse", hash)).resolves.toBe(true);
    await expect(verifyPasswordHash("wrong", hash)).resolves.toBe(false);
    await expect(verifyPasswordHash("correct horse", "plaintext-password")).resolves.toBe(false);
  });

  it("signs a bounded session and rejects tampered or expired tokens", () => {
    const token = createAdminSessionToken({ actorId, username: "reviewer", csrfToken: "csrf-ref" }, secret, 1_000);
    const request = new Request("https://example.test/admin", { headers: { Cookie: `${ADMIN_SESSION_COOKIE}=${token}` } });
    expect(readAdminSession(request, secret, 1_001)).toMatchObject({ actorId, username: "reviewer", role: "admin", expiresAt: 8 * 60 * 60 * 1000 + 1_000 });
    expect(readAdminSession(new Request("https://example.test", { headers: { Cookie: `${ADMIN_SESSION_COOKIE}=${token}x` } }), secret, 1_001)).toBeNull();
    expect(readAdminSession(request, secret, 8 * 60 * 60 * 1000 + 1_001)).toBeNull();
  });

  it("requires same-origin and a session-bound double-submit CSRF token", () => {
    const token = createAdminSessionToken({ actorId, username: "reviewer", csrfToken: "csrf-ref" }, secret, 1_000);
    const good = new Request("https://example.test/api/admin/candidates/id/decision", {
      method: "POST",
      headers: {
        Origin: "https://example.test",
        Cookie: `${ADMIN_SESSION_COOKIE}=${token}; ${ADMIN_CSRF_COOKIE}=csrf-ref`,
        "X-CSRF-Token": "csrf-ref",
      },
    });
    const session = readAdminSession(good, secret, 1_001);
    expect(session).not.toBeNull();
    expect(isSameOrigin(good)).toBe(true);
    expect(verifyCsrf(good, session)).toBe(true);
    expect(isSameOrigin(new Request(good.url, { method: "POST", headers: { Origin: "https://attacker.test" } }))).toBe(false);
    expect(verifyCsrf(new Request(good.url, { method: "POST", headers: { "X-CSRF-Token": "wrong" } }), session)).toBe(false);
  });

  it("sets strict cookie attributes and HttpOnly only on the session cookie", () => {
    const expiresAt = new Date("2026-10-02T00:00:00.000Z");
    expect(cookieOptions(ADMIN_SESSION_COOKIE, "session", expiresAt, true)).toContain("HttpOnly");
    expect(cookieOptions(ADMIN_SESSION_COOKIE, "session", expiresAt, true)).toContain("SameSite=Strict");
    expect(cookieOptions(ADMIN_SESSION_COOKIE, "session", expiresAt, true)).toContain("Secure");
    expect(cookieOptions(ADMIN_CSRF_COOKIE, "csrf", expiresAt, false)).not.toContain("HttpOnly");
    expect(cookieOptions(ADMIN_CSRF_COOKIE, "csrf", expiresAt, false)).not.toContain("Secure");
  });
});
