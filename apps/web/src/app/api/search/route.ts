import { internalErrorResponse, searchHandler } from "@/lib/public-api/handlers";
import { getPublicFacilityRepository } from "@/lib/public-api/repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  try {
    return await searchHandler(request, getPublicFacilityRepository());
  } catch {
    return internalErrorResponse();
  }
}
