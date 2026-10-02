import { authenticatedSession, mutationIsAllowed } from "@/lib/admin/session-handlers";
import { getAdminReviewRepository } from "@/lib/admin/repository";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const actions = ["RUN_NOW", "PAUSE_SYNC", "RESUME_SYNC"] as const;

export async function POST(request: Request, context: { params: Promise<{ sourceId: string }> }) {
  const session = authenticatedSession(request);
  if (!session) return Response.json({ data: null, meta: null, error: { code: "ADMIN_AUTH_REQUIRED", message: "请先登录" } }, { status: 401 });
  if (!mutationIsAllowed(request)) return Response.json({ data: null, meta: null, error: { code: "CSRF_REJECTED", message: "请求校验失败" } }, { status: 403 });
  const requestId = request.headers.get("idempotency-key") ?? "";
  if (!UUID.test(requestId)) return Response.json({ data: null, meta: null, error: { code: "IDEMPOTENCY_KEY_REQUIRED", message: "请提供有效的 Idempotency-Key" } }, { status: 400 });
  const { sourceId } = await context.params;
  if (!UUID.test(sourceId)) return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "来源标识无效" } }, { status: 400 });
  let body: unknown;
  try { body = await request.json(); } catch { return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "请求格式无效" } }, { status: 400 }); }
  const input = body as { action?: unknown; reason?: unknown };
  if (typeof input.action !== "string" || !actions.includes(input.action as typeof actions[number]) || typeof input.reason !== "string" || input.reason.trim().length < 5 || input.reason.trim().length > 500) {
    return Response.json({ data: null, meta: null, error: { code: "REASON_REQUIRED", message: "操作无效，请填写 5 至 500 个字符的理由" } }, { status: 400 });
  }
  try {
    const data = await getAdminReviewRepository().decideSync({ sourceId, actorId: session.actorId, requestId, action: input.action as typeof actions[number], reason: input.reason.trim() });
    return Response.json({ data, meta: null, error: null }, { status: input.action === "RUN_NOW" ? 202 : 200, headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const code = typeof error === "object" && error && "code" in error ? String(error.code) : "";
    const message = error instanceof Error ? error.message : "";
    if (message.includes("MANUAL_FILE_REQUIRED")) return Response.json({ data: null, meta: null, error: { code: "MANUAL_FILE_REQUIRED", message: "该来源需要人工下载文件导入" } }, { status: 409 });
    const status = code === "P0002" ? 404 : code === "23514" || code === "23505" ? 409 : code === "42501" ? 403 : 503;
    const errorCode = code === "P0002" ? "NOT_FOUND" : code === "42501" ? "ADMIN_FORBIDDEN" : code === "23505" ? "REQUEST_CONFLICT" : code === "23514" ? "SYNC_ACTION_BLOCKED" : "ADMIN_SERVICE_UNAVAILABLE";
    return Response.json({ data: null, meta: null, error: { code: errorCode, message: "同步操作未完成，请刷新状态后重试" } }, { status });
  }
}
