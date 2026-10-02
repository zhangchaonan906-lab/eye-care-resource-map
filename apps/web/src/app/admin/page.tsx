import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { readAdminSession } from "@/lib/admin/auth";
import AdminConsole from "./review-console";

export const dynamic = "force-dynamic";

export default async function AdminPage() {
  const cookieStore = await cookies();
  const requestHeaders = await headers();
  const host = requestHeaders.get("host") ?? "localhost";
  const protocol = requestHeaders.get("x-forwarded-proto") === "https" ? "https" : "http";
  const request = new Request(`${protocol}://${host}/admin`, { headers: { cookie: cookieStore.toString() } });
  const session = readAdminSession(request, process.env.ADMIN_SESSION_SECRET ?? "");
  if (!session) redirect("/admin/login");
  return <AdminConsole username={session.username} />;
}
