import { adminLogin, adminLogout, adminSessionChallenge, getAdminSession } from "@/lib/admin/session-handlers";
import { rateLimitResponse, RATE_LIMITS } from "@/lib/rate-limit/distributed";

export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const limited = await rateLimitResponse(request, RATE_LIMITS.adminLogin);
  if (limited) return limited;
  return request.headers.get("cookie")?.includes("eye_admin_session=") ? getAdminSession(request) : adminSessionChallenge();
}
export async function POST(request: Request) {
  const limited = await rateLimitResponse(request, RATE_LIMITS.adminLogin);
  return limited ?? adminLogin(request);
}
export function DELETE(request: Request) { return adminLogout(request); }
