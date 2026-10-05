import { internalErrorResponse, searchHandler } from "@/lib/public-api/handlers";
import { getPublicFacilityRepository } from "@/lib/public-api/repository";
import { rateLimitResponse, RATE_LIMITS } from "@/lib/rate-limit/distributed";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  const limited = await rateLimitResponse(request, RATE_LIMITS.search);
  if (limited) return limited;
  try {
    return await searchHandler(request, getPublicFacilityRepository());
  } catch {
    return internalErrorResponse();
  }
}
