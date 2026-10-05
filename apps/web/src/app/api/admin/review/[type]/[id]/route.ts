import { authenticatedSession } from "@/lib/admin/session-handlers";
import { getAdminReviewRepository, type ReviewType } from "@/lib/admin/repository";

export const dynamic = "force-dynamic";
const allowed = new Set<ReviewType>(["candidates", "duplicates", "locations", "facilities", "imports", "audit", "corrections"]);
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function GET(request: Request, context: { params: Promise<{ type: string; id: string }> }) {
  if (!authenticatedSession(request)) return Response.json({ data: null, meta: null, error: { code: "ADMIN_AUTH_REQUIRED", message: "请先登录" } }, { status: 401 });
  const { type, id } = await context.params;
  if (!allowed.has(type as ReviewType) || !uuid.test(id)) return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "记录标识无效" } }, { status: 400 });
  try {
    const item = await getAdminReviewRepository().get(type as ReviewType, id);
    return item ? Response.json({ data: item, meta: null, error: null }, { headers: { "Cache-Control": "no-store" } })
      : Response.json({ data: null, meta: null, error: { code: "NOT_FOUND", message: "未找到审核记录" } }, { status: 404 });
  } catch {
    return Response.json({ data: null, meta: null, error: { code: "ADMIN_SERVICE_UNAVAILABLE", message: "审核记录暂不可用" } }, { status: 503 });
  }
}
