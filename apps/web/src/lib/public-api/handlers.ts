import { FACILITY_CATEGORIES, FACILITY_CATEGORY_LABELS, type PublicFacilityRepository } from "./types";
import {
  parseFacilityQuery,
  parseNearbyQuery,
  parseSearchQuery,
  parseUuid,
  ValidationError,
  ViewportTooLargeError,
} from "./validation";

type ErrorBody = { data: null; meta: null; error: { code: string; message: string } };

function json(body: unknown, status = 200, cacheControl = "public, max-age=30, stale-while-revalidate=60"): Response {
  return Response.json(body, { status, headers: { "Cache-Control": cacheControl } });
}

function badRequest(error: ValidationError): Response {
  return json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: error.message } } satisfies ErrorBody, 400);
}

export function internalErrorResponse(cacheControl?: string): Response {
  return json({ data: null, meta: null, error: { code: "INTERNAL_ERROR", message: "服务暂不可用" } } satisfies ErrorBody, 500, cacheControl);
}

export async function facilitiesHandler(request: Request, repository: PublicFacilityRepository): Promise<Response> {
  try {
    const input = parseFacilityQuery(new URL(request.url));
    const page = await repository.list(input);
    return json({ data: page.items, meta: { count: page.items.length, nextCursor: page.nextCursor }, error: null });
  } catch (error) {
    if (error instanceof ViewportTooLargeError) {
      return json({ data: null, meta: null, error: { code: "VIEWPORT_TOO_LARGE", message: error.message } }, 400);
    }
    if (error instanceof ValidationError) return badRequest(error);
    return internalErrorResponse();
  }
}

export async function detailHandler(request: Request, id: string, repository: PublicFacilityRepository): Promise<Response> {
  try {
    const validId = parseUuid(id);
    const facility = await repository.getById(validId);
    if (!facility) return json({ data: null, meta: null, error: { code: "NOT_FOUND", message: "未找到该医疗机构" } }, 404);
    return json({ data: facility, meta: null, error: null });
  } catch (error) {
    if (error instanceof ValidationError) return badRequest(error);
    return internalErrorResponse();
  }
}

export async function searchHandler(request: Request, repository: PublicFacilityRepository): Promise<Response> {
  try {
    const input = parseSearchQuery(new URL(request.url));
    const page = await repository.search(input);
    return json({ data: page.items, meta: { count: page.items.length, nextCursor: page.nextCursor }, error: null });
  } catch (error) {
    if (error instanceof ValidationError) return badRequest(error);
    return internalErrorResponse();
  }
}

export async function nearbyHandler(request: Request, repository: PublicFacilityRepository): Promise<Response> {
  try {
    const input = parseNearbyQuery(new URL(request.url));
    const page = await repository.nearby(input);
    return json({
      data: page.items,
      meta: { count: page.items.length, radiusMeters: input.radiusMeters, truncated: page.truncated },
      error: null,
    }, 200, "no-store");
  } catch (error) {
    if (error instanceof ValidationError) {
      return json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: error.message } } satisfies ErrorBody, 400, "no-store");
    }
    return internalErrorResponse("no-store");
  }
}

export async function categoriesHandler(publishedFacilityCount = 0): Promise<Response> {
  return json({
    data: FACILITY_CATEGORIES.map((id) => ({ id, label: FACILITY_CATEGORY_LABELS[id] })),
    meta: { count: FACILITY_CATEGORIES.length, publishedFacilityCount },
    error: null,
  });
}
