import { nearbyMethodNotAllowed, nearbyPostHandler, internalErrorResponse } from "@/lib/public-api/handlers";
import { getPublicFacilityRepository } from "@/lib/public-api/repository";
import { rateLimitResponse, RATE_LIMITS } from "@/lib/rate-limit/distributed";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  return nearbyMethodNotAllowed();
}

export async function POST(request: Request): Promise<Response> {
  const limited = await rateLimitResponse(request, RATE_LIMITS.nearby);
  if (limited) return limited;
  try {
    return await nearbyPostHandler(request, getPublicFacilityRepository());
  } catch {
    return internalErrorResponse("no-store");
  }
}
