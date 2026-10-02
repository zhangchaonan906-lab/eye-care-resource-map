import { scryptSync } from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ADMIN_CSRF_COOKIE, ADMIN_SESSION_COOKIE, createAdminSessionToken } from "./auth";
import { adminLogin, adminLogout, adminSessionChallenge, mutationIsAllowed } from "./session-handlers";

const actorId = "00000000-0000-4000-8000-000000001111";
const secret = "p11-session-secret-that-is-longer-than-32-characters";
const salt = "0123456789abcdef0123456789abcdef";
const password = "synthetic p11 password";
const hash = `scrypt$16384$8$1$${Buffer.from(salt).toString("base64url")}$${scryptSync(password, salt, 64, { N: 16384, r: 8, p: 1, maxmem: 64 * 1024 * 1024 }).toString("base64url")}`;

function setupEnvironment() {
  vi.stubEnv("ADMIN_USERNAME", "reviewer");
  vi.stubEnv("ADMIN_PASSWORD_HASH", hash);
  vi.stubEnv("ADMIN_SESSION_SECRET", secret);
  vi.stubEnv("ADMIN_ACTOR_ID", actorId);
  vi.stubEnv("ADMIN_DATABASE_URL", "postgresql://admin@admin-db/eye");
  vi.stubEnv("PUBLIC_API_DATABASE_URL", "postgresql://public@api-db/eye");
}

afterEach(() => vi.unstubAllEnvs());

describe("admin session handlers", () => {
  it("creates a pre-login CSRF challenge, accepts valid credentials, and sets secure production cookies", async () => {
    setupEnvironment(); vi.stubEnv("NODE_ENV", "production");
    const challenge = adminSessionChallenge();
    const data = await challenge.json();
    const preCookie = challenge.headers.getSetCookie().find((cookie) => cookie.startsWith("eye_admin_pre_csrf="));
    expect(preCookie).toContain("SameSite=Strict");
    expect(preCookie).toContain("Secure");
    const response = await adminLogin(new Request("https://app.example.test/api/admin/session", {
      method: "POST", headers: { Origin: "https://app.example.test", Cookie: preCookie?.split(";")[0] ?? "", "X-CSRF-Token": data.data.csrfToken, "Content-Type": "application/json" },
      body: JSON.stringify({ username: "reviewer", password }),
    }));
    expect(response.status).toBe(200);
    const sessionCookie = response.headers.getSetCookie().find((cookie) => cookie.startsWith(`${ADMIN_SESSION_COOKIE}=`)) ?? "";
    expect(sessionCookie).toContain("HttpOnly"); expect(sessionCookie).toContain("SameSite=Strict"); expect(sessionCookie).toContain("Secure");
    expect(response.headers.getSetCookie().find((cookie) => cookie.startsWith(`${ADMIN_CSRF_COOKIE}=`))).not.toContain("HttpOnly");
    const body = await response.json();
    expect(body.data.expiresAt).toBeTruthy();
    expect(JSON.stringify(body)).not.toContain(password);
  });

  it("returns the same generic response for an unknown user and a wrong password", async () => {
    setupEnvironment();
    const challenge = adminSessionChallenge(); const data = await challenge.json();
    const preCookie = challenge.headers.getSetCookie().find((cookie) => cookie.startsWith("eye_admin_pre_csrf="))?.split(";")[0] ?? "";
    const makeRequest = (username: string, submittedPassword: string) => new Request("https://app.example.test/api/admin/session", {
      method: "POST", headers: { Origin: "https://app.example.test", Cookie: preCookie, "X-CSRF-Token": data.data.csrfToken, "Content-Type": "application/json" },
      body: JSON.stringify({ username, password: submittedPassword }),
    });
    const unknown = await adminLogin(makeRequest("unknown", password));
    const wrong = await adminLogin(makeRequest("reviewer", "incorrect"));
    expect(unknown.status).toBe(401); expect(wrong.status).toBe(401);
    expect(await unknown.json()).toEqual(await wrong.json());
  });

  it("rejects missing, wrong, and cross-origin CSRF values and clears cookies on valid logout", async () => {
    setupEnvironment();
    const sessionCsrf = "test-csrf-token";
    const token = createAdminSessionToken({ actorId, username: "reviewer", csrfToken: sessionCsrf }, secret);
    const base = { method: "DELETE", Cookie: `${ADMIN_SESSION_COOKIE}=${token}; ${ADMIN_CSRF_COOKIE}=${sessionCsrf}` };
    expect(adminLogout(new Request("https://app.example.test/api/admin/session", { ...base, headers: base.Cookie ? { Cookie: base.Cookie, Origin: "https://app.example.test" } : {} })).status).toBe(403);
    expect(adminLogout(new Request("https://app.example.test/api/admin/session", { method: "DELETE", headers: { Cookie: `${ADMIN_SESSION_COOKIE}=${token}; ${ADMIN_CSRF_COOKIE}=wrong`, Origin: "https://app.example.test", "X-CSRF-Token": "wrong" } })).status).toBe(403);
    const crossOrigin = new Request("https://app.example.test/api/admin/session", { method: "DELETE", headers: { Cookie: base.Cookie, Origin: "https://attacker.test", "X-CSRF-Token": sessionCsrf } });
    expect(adminLogout(crossOrigin).status).toBe(403);
    const valid = new Request("https://app.example.test/api/admin/session", { method: "DELETE", headers: { Cookie: base.Cookie, Origin: "https://app.example.test", "X-CSRF-Token": sessionCsrf } });
    expect(mutationIsAllowed(valid)).toBe(true);
    const response = adminLogout(valid);
    expect(response.status).toBe(200);
    expect(response.headers.getSetCookie().filter((cookie) => cookie.includes("Expires=Thu, 01 Jan 1970")).length).toBe(2);
  });
});
