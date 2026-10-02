import { adminLogin, adminLogout, adminSessionChallenge, getAdminSession } from "@/lib/admin/session-handlers";

export const dynamic = "force-dynamic";
export function GET(request: Request) {
  return request.headers.get("cookie")?.includes("eye_admin_session=") ? getAdminSession(request) : adminSessionChallenge();
}
export function POST(request: Request) { return adminLogin(request); }
export function DELETE(request: Request) { return adminLogout(request); }
