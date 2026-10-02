import { nearbyMethodNotAllowed, nearbyPostHandler, internalErrorResponse } from "@/lib/public-api/handlers";
import { getPublicFacilityRepository } from "@/lib/public-api/repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  return nearbyMethodNotAllowed();
}

export async function POST(request: Request): Promise<Response> {
  try {
    return await nearbyPostHandler(request, getPublicFacilityRepository());
  } catch {
    return internalErrorResponse("no-store");
  }
}
