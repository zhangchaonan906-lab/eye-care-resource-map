export const CORRECTION_TYPES = ["institution_info", "moved", "closed", "ophthalmology_services", "coordinates", "source_issue"] as const;
export type CorrectionType = typeof CORRECTION_TYPES[number];
export type CorrectionInput = { facilityId?: string; type: CorrectionType; description: string };

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function parseCorrectionInput(value: unknown): CorrectionInput | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const input = value as Record<string, unknown>;
  if (input.facilityId !== undefined && (typeof input.facilityId !== "string" || !uuid.test(input.facilityId))) return null;
  if (typeof input.type !== "string" || !CORRECTION_TYPES.includes(input.type as CorrectionType)) return null;
  if (typeof input.description !== "string") return null;
  const description = input.description.trim();
  if (description.length < 10 || description.length > 1000) return null;
  return { ...(typeof input.facilityId === "string" ? { facilityId: input.facilityId } : {}), type: input.type as CorrectionType, description };
}

export function isSameOriginRequest(request: Request): boolean {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (!origin || !host) return false;
  try { return new URL(origin).host.toLowerCase() === host.toLowerCase(); } catch { return false; }
}
