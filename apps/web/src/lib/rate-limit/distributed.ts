import { createHmac } from "node:crypto";
import { isIP } from "node:net";

export type RateLimitPolicy = { name: string; limit: number; windowSeconds: number };
export type RateLimitResult = { allowed: boolean; limit: number; remaining: number; retryAfterSeconds: number };

const localWindows = new Map<string, { count: number; resetAt: number }>();
const incrementScript = "local count=redis.call('INCR',KEYS[1]); if count==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]); end; return {count,redis.call('TTL',KEYS[1])}";

function clientKey(request: Request, policy: RateLimitPolicy): string | null {
  if (process.env.P13_SYSTEM_TEST_MODE === "true") {
    const secret = process.env.RATE_LIMIT_HASH_SECRET;
    if (!secret) return null;
    const digest = createHmac("sha256", secret).update("p13-system-test").digest("hex");
    return `eye-map:rl:${policy.name}:${digest}`;
  }
  const trustedProxy = process.env.TRUST_PROXY_HEADERS === "true";
  const clientAddress = trustedProxy
    ? request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || request.headers.get("x-real-ip")?.trim()
      || undefined
    : process.env.APP_ENV === "production" || process.env.APP_ENV === "staging" ? null : "shared";
  if (!clientAddress) return null;
  if (trustedProxy && clientAddress !== "p13-system-test" && !isIP(clientAddress)) return null;
  const secret = process.env.RATE_LIMIT_HASH_SECRET ?? (process.env.APP_ENV === "production" || process.env.APP_ENV === "staging" ? "" : "local-development-only");
  if (!secret) return null;
  const digest = createHmac("sha256", secret).update(clientAddress).digest("hex");
  return `eye-map:rl:${policy.name}:${digest}`;
}

function localCheck(key: string, policy: RateLimitPolicy, now: number): RateLimitResult {
  const current = localWindows.get(key);
  if (!current || current.resetAt <= now) {
    localWindows.set(key, { count: 1, resetAt: now + policy.windowSeconds * 1000 });
    return { allowed: true, limit: policy.limit, remaining: policy.limit - 1, retryAfterSeconds: 0 };
  }
  current.count += 1;
  const retryAfterSeconds = Math.max(1, Math.ceil((current.resetAt - now) / 1000));
  return { allowed: current.count <= policy.limit, limit: policy.limit, remaining: Math.max(0, policy.limit - current.count), retryAfterSeconds: current.count > policy.limit ? retryAfterSeconds : 0 };
}

export async function checkRateLimit(request: Request, policy: RateLimitPolicy, now = Date.now()): Promise<RateLimitResult> {
  const key = clientKey(request, policy);
  if (!key) throw new Error("RATE_LIMIT_IDENTITY_UNAVAILABLE");
  if (process.env.P13_SYSTEM_TEST_MODE === "true") return localCheck(key, policy, now);
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) {
    if (process.env.APP_ENV === "production" || process.env.APP_ENV === "staging") throw new Error("RATE_LIMIT_BACKEND_UNAVAILABLE");
    return localCheck(key, policy, now);
  }
  try {
    const endpoint = new URL(url);
    if ((endpoint.protocol !== "https:" && process.env.P13_SYSTEM_TEST_MODE !== "true")
      || endpoint.username || endpoint.password || endpoint.search || endpoint.hash) throw new Error("invalid limiter URL");
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(["EVAL", incrementScript, "1", key, String(policy.windowSeconds)]),
      cache: "no-store",
      signal: AbortSignal.timeout(2000),
    });
    if (!response.ok) throw new Error("redis request failed");
    const payload = await response.json() as { result?: unknown; error?: unknown };
    if (payload.error || !Array.isArray(payload.result)) throw new Error("redis response invalid");
    const count = Number(payload.result[0]);
    const ttl = Number(payload.result[1]);
    if (!Number.isInteger(count) || count < 1 || !Number.isInteger(ttl)) throw new Error("redis response invalid");
    return {
      allowed: count <= policy.limit,
      limit: policy.limit,
      remaining: Math.max(0, policy.limit - count),
      retryAfterSeconds: count > policy.limit ? Math.max(1, ttl) : 0,
    };
  } catch {
    throw new Error("RATE_LIMIT_BACKEND_UNAVAILABLE");
  }
}

export async function rateLimitResponse(request: Request, policy: RateLimitPolicy): Promise<Response | null> {
  try {
    const result = await checkRateLimit(request, policy);
    if (result.allowed) return null;
    return Response.json({ data: null, meta: null, error: { code: "RATE_LIMITED", message: "请求过于频繁，请稍后重试" } }, {
      status: 429,
      headers: { "Cache-Control": "no-store", "Retry-After": String(result.retryAfterSeconds), "RateLimit-Limit": String(result.limit), "RateLimit-Remaining": "0" },
    });
  } catch {
    return Response.json({ data: null, meta: null, error: { code: "SERVICE_UNAVAILABLE", message: "服务暂不可用，请稍后重试" } }, {
      status: 503,
      headers: { "Cache-Control": "no-store", "Retry-After": "30" },
    });
  }
}

export const RATE_LIMITS = {
  facilities: { name: "facilities", limit: 120, windowSeconds: 60 },
  detail: { name: "detail", limit: 120, windowSeconds: 60 },
  search: { name: "search", limit: 60, windowSeconds: 60 },
  nearby: { name: "nearby", limit: 30, windowSeconds: 60 },
  correction: { name: "correction", limit: 5, windowSeconds: 3600 },
  adminSession: { name: "admin-session", limit: 120, windowSeconds: 60 },
  adminLogin: { name: "admin-login", limit: 10, windowSeconds: 60 },
} satisfies Record<string, RateLimitPolicy>;
