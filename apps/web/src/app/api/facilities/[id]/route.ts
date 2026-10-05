import { detailHandler, internalErrorResponse } from "@/lib/public-api/handlers";
import { getPublicFacilityRepository } from "@/lib/public-api/repository";
import { rateLimitResponse, RATE_LIMITS } from "@/lib/rate-limit/distributed";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ id: string }> }): Promise<Response> {
  const limited = await rateLimitResponse(request, RATE_LIMITS.detail);
  if (limited) return limited;
  try {
    const { id } = await context.params;
    return await detailHandler(request, id, getPublicFacilityRepository());
  } catch {
    return internalErrorResponse();
  }
}
