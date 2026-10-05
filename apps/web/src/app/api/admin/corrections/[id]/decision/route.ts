import { authenticatedSession, mutationIsAllowed } from "@/lib/admin/session-handlers";
import { getAdminReviewRepository } from "@/lib/admin/repository";

export const dynamic = "force-dynamic";
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const actions = new Set(["START_REVIEW", "RESOLVE", "DISMISS"]);

export async function POST(request: Request, context: { params: Promise<{ id: string }> }): Promise<Response> {
  const session = authenticatedSession(request);
  if (!session) return Response.json({ data: null, meta: null, error: { code: "ADMIN_AUTH_REQUIRED", message: "请先登录" } }, { status: 401, headers: { "Cache-Control": "no-store" } });
  if (!mutationIsAllowed(request)) return Response.json({ data: null, meta: null, error: { code: "CSRF_REJECTED", message: "请求校验失败" } }, { status: 403, headers: { "Cache-Control": "no-store" } });
  const { id } = await context.params;
  const requestId = request.headers.get("idempotency-key") ?? "";
  if (!uuid.test(id) || !uuid.test(requestId)) return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "操作标识无效" } }, { status: 400, headers: { "Cache-Control": "no-store" } });
  let body: unknown;
  try { body = await request.json(); } catch { return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "提交内容无效" } }, { status: 400, headers: { "Cache-Control": "no-store" } }); }
  const input = body as { action?: unknown; reason?: unknown };
  if (typeof input.action !== "string" || !actions.has(input.action) || typeof input.reason !== "string" || input.reason.trim().length < 5 || input.reason.trim().length > 500) {
    return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "请检查审核操作和理由" } }, { status: 400, headers: { "Cache-Control": "no-store" } });
  }
  try {
    const result = await getAdminReviewRepository().decideCorrection({ reportId: id, actorId: session.actorId, requestId, action: input.action as "START_REVIEW" | "RESOLVE" | "DISMISS", reason: input.reason.trim() });
    return Response.json({ data: result, meta: null, error: null }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ data: null, meta: null, error: { code: "ADMIN_SERVICE_UNAVAILABLE", message: "纠错审核操作暂不可用" } }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}
