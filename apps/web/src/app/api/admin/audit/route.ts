import { authenticatedSession } from "@/lib/admin/session-handlers";
import { getAdminReviewRepository } from "@/lib/admin/repository";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  if (!authenticatedSession(request)) return Response.json({ data: null, meta: null, error: { code: "ADMIN_AUTH_REQUIRED", message: "请先登录" } }, { status: 401 });
  const url = new URL(request.url);
  const limit = Number(url.searchParams.get("limit") ?? "25");
  const cursor = url.searchParams.get("cursor") ?? undefined;
  if (!Number.isInteger(limit) || limit < 1 || limit > 100 || (cursor && !/^[0-9a-f-]{36}$/i.test(cursor))) {
    return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "分页参数无效" } }, { status: 400 });
  }
  try {
    const page = await getAdminReviewRepository().list("audit", { limit, cursor });
    return Response.json({ data: page.items, meta: { count: page.items.length, nextCursor: page.nextCursor }, error: null }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ data: null, meta: null, error: { code: "ADMIN_SERVICE_UNAVAILABLE", message: "审计记录暂不可用" } }, { status: 503 });
  }
}
