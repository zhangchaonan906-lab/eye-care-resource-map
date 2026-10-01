import {
  ADMIN_CSRF_COOKIE,
  ADMIN_SESSION_COOKIE,
  cookieOptions,
  createAdminSessionToken,
  createCsrfToken,
  isSameOrigin,
  parseCookies,
  readAdminSession,
  tokensEqual,
  verifyCsrf,
  verifyPasswordHash,
} from "./auth";

const PRELOGIN_CSRF_COOKIE = "eye_admin_pre_csrf";
const SESSION_MS = 8 * 60 * 60 * 1000;
const jsonHeaders = { "Cache-Control": "no-store", "Content-Type": "application/json; charset=utf-8" };
const invalidLogin = { data: null, meta: null, error: { code: "INVALID_CREDENTIALS", message: "用户名或密码错误" } };

function appendCookie(headers: Headers, cookie: string): void {
  headers.append("Set-Cookie", cookie);
}

function secureCookie(): boolean {
  return process.env.NODE_ENV === "production";
}

export function adminSessionChallenge(): Response {
  const csrf = createCsrfToken();
  const headers = new Headers(jsonHeaders);
  appendCookie(headers, cookieOptions(PRELOGIN_CSRF_COOKIE, csrf, new Date(Date.now() + 10 * 60 * 1000), secureCookie()));
  return Response.json({ data: { csrfToken: csrf }, meta: null, error: null }, { headers });
}

export async function adminLogin(request: Request): Promise<Response> {
  if (!isSameOrigin(request)) return Response.json({ data: null, meta: null, error: { code: "CSRF_REJECTED", message: "请求校验失败" } }, { status: 403, headers: jsonHeaders });
  const cookies = parseCookies(request.headers.get("cookie") ?? "");
  const preloginToken = cookies.get(PRELOGIN_CSRF_COOKIE);
  const headerToken = request.headers.get("x-csrf-token");
  if (!preloginToken || !headerToken || !tokensEqual(preloginToken, headerToken)) {
    return Response.json({ data: null, meta: null, error: { code: "CSRF_REJECTED", message: "请求校验失败" } }, { status: 403, headers: jsonHeaders });
  }
  const expectedUsername = process.env.ADMIN_USERNAME ?? "";
  const passwordHash = process.env.ADMIN_PASSWORD_HASH ?? "";
  const actorId = process.env.ADMIN_ACTOR_ID ?? "";
  const secret = process.env.ADMIN_SESSION_SECRET ?? "";
  if (!expectedUsername || !passwordHash || !actorId || secret.length < 32 || !process.env.ADMIN_DATABASE_URL
      || process.env.ADMIN_DATABASE_URL === process.env.PUBLIC_API_DATABASE_URL) {
    return Response.json({ data: null, meta: null, error: { code: "ADMIN_NOT_CONFIGURED", message: "管理服务未配置" } }, { status: 503, headers: jsonHeaders });
  }
  try {
    if (!process.env.PUBLIC_API_DATABASE_URL
      || new URL(process.env.ADMIN_DATABASE_URL).username === new URL(process.env.PUBLIC_API_DATABASE_URL).username) {
      return Response.json({ data: null, meta: null, error: { code: "ADMIN_NOT_CONFIGURED", message: "管理服务未配置" } }, { status: 503, headers: jsonHeaders });
    }
  } catch {
    return Response.json({ data: null, meta: null, error: { code: "ADMIN_NOT_CONFIGURED", message: "管理服务未配置" } }, { status: 503, headers: jsonHeaders });
  }
  let body: unknown;
  try { body = await request.json(); } catch { return Response.json(invalidLogin, { status: 401, headers: jsonHeaders }); }
  const input = body as { username?: unknown; password?: unknown };
  const username = typeof input.username === "string" ? input.username : "";
  const password = typeof input.password === "string" ? input.password : "";
  const passwordValid = await verifyPasswordHash(password, passwordHash);
  if (username !== expectedUsername || !passwordValid) return Response.json(invalidLogin, { status: 401, headers: jsonHeaders });

  const now = Date.now();
  const csrfToken = createCsrfToken();
  const token = createAdminSessionToken({ actorId, username: expectedUsername, csrfToken }, secret, now);
  const expiresAt = new Date(now + SESSION_MS);
  const headers = new Headers(jsonHeaders);
  appendCookie(headers, cookieOptions(ADMIN_SESSION_COOKIE, token, expiresAt, secureCookie()));
  appendCookie(headers, cookieOptions(ADMIN_CSRF_COOKIE, csrfToken, expiresAt, secureCookie()));
  appendCookie(headers, cookieOptions(PRELOGIN_CSRF_COOKIE, "", new Date(0), secureCookie()));
  return Response.json({ data: { csrfToken, expiresAt: expiresAt.toISOString() }, meta: null, error: null }, { headers });
}

export function adminLogout(request: Request): Response {
  const session = readAdminSession(request, process.env.ADMIN_SESSION_SECRET ?? "");
  if (!isSameOrigin(request) || !verifyCsrf(request, session)) {
    return Response.json({ data: null, meta: null, error: { code: "CSRF_REJECTED", message: "请求校验失败" } }, { status: 403, headers: jsonHeaders });
  }
  const headers = new Headers(jsonHeaders);
  appendCookie(headers, cookieOptions(ADMIN_SESSION_COOKIE, "", new Date(0), secureCookie()));
  appendCookie(headers, cookieOptions(ADMIN_CSRF_COOKIE, "", new Date(0), secureCookie()));
  return Response.json({ data: { loggedOut: true }, meta: null, error: null }, { headers });
}

export function getAdminSession(request: Request): Response {
  const session = readAdminSession(request, process.env.ADMIN_SESSION_SECRET ?? "");
  if (!session) return Response.json({ data: null, meta: null, error: { code: "ADMIN_AUTH_REQUIRED", message: "请先登录" } }, { status: 401, headers: jsonHeaders });
  return Response.json({ data: { actorId: session.actorId, username: session.username, role: session.role, expiresAt: new Date(session.expiresAt).toISOString(), csrfToken: session.csrfToken }, meta: null, error: null }, { headers: jsonHeaders });
}

export function authenticatedSession(request: Request) {
  return readAdminSession(request, process.env.ADMIN_SESSION_SECRET ?? "");
}

export function mutationIsAllowed(request: Request): boolean {
  return isSameOrigin(request) && verifyCsrf(request, authenticatedSession(request));
}
