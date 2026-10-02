import { versionResponse } from "@/lib/release/endpoints";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  return versionResponse();
}
