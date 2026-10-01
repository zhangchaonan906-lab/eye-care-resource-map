import { categoriesHandler, internalErrorResponse } from "@/lib/public-api/handlers";
import { getPublicFacilityRepository } from "@/lib/public-api/repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  try {
    const count = await getPublicFacilityRepository().countPublished();
    return await categoriesHandler(count);
  } catch {
    return internalErrorResponse();
  }
}
