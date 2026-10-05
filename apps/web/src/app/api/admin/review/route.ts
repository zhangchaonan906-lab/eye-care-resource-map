import { authenticatedSession } from "@/lib/admin/session-handlers";
import { getAdminReviewRepository, type ReviewType } from "@/lib/admin/repository";

export const dynamic = "force-dynamic";
const types: ReviewType[] = ["candidates", "duplicates", "locations", "facilities", "imports", "audit", "corrections"];
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function GET(request: Request) {
  if (!authenticatedSession(request)) return Response.json({ data: null, meta: null, error: { code: "ADMIN_AUTH_REQUIRED", message: "请先登录" } }, { status: 401 });
  const url = new URL(request.url);
  const type = url.searchParams.get("type") as ReviewType | null;
  if (!type || !types.includes(type)) return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "队列类型无效" } }, { status: 400 });
  const limit = Number(url.searchParams.get("limit") ?? "25");
  const cursor = url.searchParams.get("cursor") ?? undefined;
  const sourceId = url.searchParams.get("source") ?? undefined;
  const region = url.searchParams.get("region") ?? undefined;
  if (!Number.isInteger(limit) || limit < 1 || limit > 100 || (cursor && !uuid.test(cursor)) || (sourceId && !uuid.test(sourceId)) || (region && !/^\d{2,6}$/.test(region))) {
    return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "筛选条件无效" } }, { status: 400 });
  }
  try {
    const result = await getAdminReviewRepository().list(type, { limit, cursor, status: url.searchParams.get("status") ?? undefined, sourceId, region });
    return Response.json({ data: result.items, meta: { count: result.items.length, nextCursor: result.nextCursor }, error: null }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ data: null, meta: null, error: { code: "ADMIN_SERVICE_UNAVAILABLE", message: "审核队列暂不可用" } }, { status: 503 });
  }
}
