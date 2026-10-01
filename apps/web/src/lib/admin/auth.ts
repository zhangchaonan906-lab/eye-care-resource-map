import { createHmac, randomBytes, scrypt as scryptCallback, timingSafeEqual } from "node:crypto";
export const ADMIN_SESSION_COOKIE = "eye_admin_session";
export const ADMIN_CSRF_COOKIE = "eye_admin_csrf";
const SESSION_DURATION_MS = 8 * 60 * 60 * 1000;
const SCRYPT_N = 16_384;
const SCRYPT_R = 8;
const SCRYPT_P = 1;
const SCRYPT_KEY_LENGTH = 64;

export type AdminSession = {
  actorId: string;
  username: string;
  role: "admin";
  expiresAt: number;
  csrfToken: string;
};

type SessionInput = Pick<AdminSession, "actorId" | "username" | "csrfToken">;

function safeEqual(left: string, right: string): boolean {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function tokensEqual(left: string, right: string): boolean {
  return safeEqual(left, right);
}

export async function verifyPasswordHash(password: string, encoded: string): Promise<boolean> {
  try {
    const match = /^scrypt\$(\d+)\$(\d+)\$(\d+)\$([A-Za-z0-9_-]+)\$([A-Za-z0-9_-]+)$/.exec(encoded);
    if (!match) return false;
    const [, nText, rText, pText, saltText, digestText] = match;
    const n = Number(nText);
    const r = Number(rText);
    const p = Number(pText);
    if (n !== SCRYPT_N || r !== SCRYPT_R || p !== SCRYPT_P) return false;
    const salt = Buffer.from(saltText, "base64url");
    const expected = Buffer.from(digestText, "base64url");
    if (salt.length < 16 || expected.length !== SCRYPT_KEY_LENGTH) return false;
    const actual = await new Promise<Buffer>((resolve, reject) => {
      scryptCallback(password, salt, expected.length, { N: n, r, p, maxmem: 64 * 1024 * 1024 }, (error, key) => {
        if (error) reject(error); else resolve(key as Buffer);
      });
    });
    return timingSafeEqual(actual, expected);
  } catch {
    return false;
  }
}

export function createAdminSessionToken(input: SessionInput, secret: string, now = Date.now()): string {
  if (secret.length < 32) throw new Error("ADMIN_SESSION_SECRET must contain at least 32 characters");
  const payload: AdminSession = { ...input, role: "admin", expiresAt: now + SESSION_DURATION_MS };
  const encoded = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = createHmac("sha256", secret).update(encoded).digest("base64url");
  return `${encoded}.${signature}`;
}

export function readAdminSession(request: Request, secret: string, now = Date.now()): AdminSession | null {
  if (secret.length < 32) return null;
  const cookies = parseCookies(request.headers.get("cookie") ?? "");
  const token = cookies.get(ADMIN_SESSION_COOKIE);
  if (!token) return null;
  const [encoded, signature, extra] = token.split(".");
  if (!encoded || !signature || extra !== undefined) return null;
  const expected = createHmac("sha256", secret).update(encoded).digest("base64url");
  if (!safeEqual(signature, expected)) return null;
  try {
    const value = JSON.parse(Buffer.from(encoded, "base64url").toString("utf8")) as Partial<AdminSession>;
    if (value.role !== "admin" || typeof value.actorId !== "string" || typeof value.username !== "string"
      || typeof value.csrfToken !== "string" || !value.csrfToken || typeof value.expiresAt !== "number"
      || !Number.isFinite(value.expiresAt) || value.expiresAt <= now) return null;
    return value as AdminSession;
  } catch {
    return null;
  }
}

export function isSameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return false;
  try {
    return new URL(origin).origin === new URL(request.url).origin;
  } catch {
    return false;
  }
}

export function verifyCsrf(request: Request, session: AdminSession | null): boolean {
  if (!session) return false;
  const cookies = parseCookies(request.headers.get("cookie") ?? "");
  const cookieToken = cookies.get(ADMIN_CSRF_COOKIE);
  const headerToken = request.headers.get("x-csrf-token");
  return Boolean(cookieToken && headerToken && safeEqual(cookieToken, session.csrfToken)
    && safeEqual(headerToken, session.csrfToken));
}

export function createCsrfToken(): string {
  return randomBytes(32).toString("base64url");
}

export function cookieOptions(name: string, value: string, expiresAt: Date, secure: boolean): string {
  const flags = [`${name}=${encodeURIComponent(value)}`, "Path=/", `Expires=${expiresAt.toUTCString()}`, "SameSite=Strict"];
  if (name === ADMIN_SESSION_COOKIE) flags.push("HttpOnly");
  if (secure) flags.push("Secure");
  return flags.join("; ");
}

export function parseCookies(value: string): Map<string, string> {
  const cookies = new Map<string, string>();
  for (const part of value.split(";")) {
    const separator = part.indexOf("=");
    if (separator < 1) continue;
    const name = part.slice(0, separator).trim();
    try { cookies.set(name, decodeURIComponent(part.slice(separator + 1).trim())); } catch { /* ignore malformed cookie */ }
  }
  return cookies;
}
