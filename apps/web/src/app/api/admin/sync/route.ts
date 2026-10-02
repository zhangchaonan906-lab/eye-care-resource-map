import { authenticatedSession } from "@/lib/admin/session-handlers";
import { getAdminReviewRepository, type SyncReviewType } from "@/lib/admin/repository";

export const dynamic = "force-dynamic";
const types: SyncReviewType[] = ["policies", "tasks", "alerts"];
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function GET(request: Request) {
  if (!authenticatedSession(request)) return Response.json({ data: null, meta: null, error: { code: "ADMIN_AUTH_REQUIRED", message: "请先登录" } }, { status: 401 });
  const url = new URL(request.url);
  const type = url.searchParams.get("type") as SyncReviewType | null;
  const limit = Number(url.searchParams.get("limit") ?? "25");
  const cursor = url.searchParams.get("cursor") ?? undefined;
  if (!type || !types.includes(type) || !Number.isInteger(limit) || limit < 1 || limit > 100 || (cursor && !uuid.test(cursor))) {
    return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "同步队列参数无效" } }, { status: 400 });
  }
  try {
    const page = await getAdminReviewRepository().listSync(type, { limit, cursor, status: url.searchParams.get("status") ?? undefined });
    return Response.json({ data: page.items, meta: { count: page.items.length, nextCursor: page.nextCursor }, error: null }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ data: null, meta: null, error: { code: "ADMIN_SERVICE_UNAVAILABLE", message: "同步队列暂不可用" } }, { status: 503 });
  }
}
