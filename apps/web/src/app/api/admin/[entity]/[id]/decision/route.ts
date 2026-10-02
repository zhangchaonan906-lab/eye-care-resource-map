import { authenticatedSession, mutationIsAllowed } from "@/lib/admin/session-handlers";
import { getAdminReviewRepository } from "@/lib/admin/repository";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const entityMap: Record<string, string> = { candidates: "candidate", duplicates: "duplicate", locations: "location", facilities: "facility" };

export async function POST(request: Request, context: { params: Promise<{ entity: string; id: string }> }) {
  const session = authenticatedSession(request);
  if (!session) return Response.json({ data: null, meta: null, error: { code: "ADMIN_AUTH_REQUIRED", message: "请先登录" } }, { status: 401 });
  if (!mutationIsAllowed(request)) return Response.json({ data: null, meta: null, error: { code: "CSRF_REJECTED", message: "请求校验失败" } }, { status: 403 });
  const idempotencyKey = request.headers.get("idempotency-key") ?? "";
  if (!UUID.test(idempotencyKey)) return Response.json({ data: null, meta: null, error: { code: "IDEMPOTENCY_KEY_REQUIRED", message: "请提供有效的 Idempotency-Key" } }, { status: 400 });
  const { entity, id } = await context.params;
  const mapped = entityMap[entity];
  if (!mapped || !UUID.test(id)) return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "决策对象无效" } }, { status: 400 });
  let body: unknown;
  try { body = await request.json(); } catch { return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "请求格式无效" } }, { status: 400 }); }
  const input = body as { action?: unknown; reason?: unknown; [key: string]: unknown };
  if (typeof input.action !== "string" || typeof input.reason !== "string" || input.reason.trim().length < 5 || input.reason.trim().length > 500) {
    return Response.json({ data: null, meta: null, error: { code: "REASON_REQUIRED", message: "请填写 5 至 500 个字符的审核理由" } }, { status: 400 });
  }
  try {
    const data = await getAdminReviewRepository().decide({
      requestId: idempotencyKey, actorId: session.actorId, entity: mapped, entityId: id,
      action: input.action, reason: input.reason.trim(),
      payload: Object.fromEntries(Object.entries(input).filter(([key]) => !["action", "reason", "actor_id", "actorId"].includes(key))),
    });
    return Response.json({ data, meta: null, error: null }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const code = typeof error === "object" && error && "code" in error ? String(error.code) : "";
    const message = error instanceof Error ? error.message : "";
    const status = code === "40001" ? 409 : code === "42501" ? 403 : code === "P0002" ? 404 : code === "23514" ? 409 : 503;
    const errorCode = code === "40001" ? "REVIEW_STATE_CONFLICT" : code === "P0002" ? "NOT_FOUND" : code === "23514" ? "ACTION_BLOCKED" : code === "42501" ? "ADMIN_FORBIDDEN" : "ADMIN_SERVICE_UNAVAILABLE";
    console.warn(JSON.stringify({ actorId: session.actorId, action: input.action, entity: mapped, entityId: id, result: "blocked", reasonCode: errorCode }));
    return Response.json({ data: null, meta: null, error: { code: errorCode, message: errorCode === "ACTION_BLOCKED" ? message.replace(/^PUBLISH_BLOCKED:/, "发布条件未满足：") : errorCode === "REVIEW_STATE_CONFLICT" ? "记录状态已变化，请刷新后重试" : errorCode === "NOT_FOUND" ? "未找到审核对象" : "审核操作暂不可用" } }, { status });
  }
}
