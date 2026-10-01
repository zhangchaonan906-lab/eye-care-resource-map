import type { PublicFacilityRepository } from "./types";
import {
  parseFacilityQuery,
  parseSearchQuery,
  parseUuid,
  ValidationError,
  ViewportTooLargeError,
} from "./validation";

type ErrorBody = { data: null; meta: null; error: { code: string; message: string } };

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status, headers: { "Cache-Control": "public, max-age=30, stale-while-revalidate=60" } });
}

function badRequest(error: ValidationError): Response {
  return json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: error.message } } satisfies ErrorBody, 400);
}

export function internalErrorResponse(): Response {
  return json({ data: null, meta: null, error: { code: "INTERNAL_ERROR", message: "服务暂不可用" } } satisfies ErrorBody, 500);
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

export async function categoriesHandler(): Promise<Response> {
  return json({
    data: [
      { id: "eye_specialty_hospital", label: "眼科专科医院" },
      { id: "general_hospital_ophthalmology", label: "设有眼科的综合医院" },
      { id: "ophthalmology_center", label: "眼科中心" },
      { id: "eye_clinic", label: "眼科诊所" },
      { id: "unknown", label: "待核验" },
    ],
    meta: { count: 5 },
    error: null,
  });
}
