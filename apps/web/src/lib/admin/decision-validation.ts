const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const ALLOWED_ACTIONS: Record<string, ReadonlySet<string>> = {
  candidate: new Set(["CREATE_FACILITY", "MATCH_EXISTING_FACILITY", "REJECT_CANDIDATE"]),
  duplicate: new Set(["MERGE", "SEPARATE", "REJECT_DUPLICATE", "REOPEN_DUPLICATE_CASE"]),
  location: new Set(["VERIFY_LOCATION", "REJECT_LOCATION", "PROMOTE_LOCATION"]),
  facility: new Set(["VERIFY_FACILITY", "PUBLISH", "RETURN_TO_REVIEW", "WITHDRAW"]),
};
const IDENTIFIER_FIELDS = ["targetFacilityId", "primaryCandidateId", "regionId"] as const;
const TEXT_CONTROL = /[\u0000-\u001f\u007f-\u009f]/;

export type AdminDecisionInput = {
  action: string;
  reason: string;
  payload: Record<string, unknown>;
};

export function validateAdminDecisionInput(entity: string, input: unknown): AdminDecisionInput | null {
  if (!input || typeof input !== "object" || Array.isArray(input)) return null;
  const body = input as Record<string, unknown>;
  if (typeof body.action !== "string" || !ALLOWED_ACTIONS[entity]?.has(body.action)) return null;
  if (typeof body.reason !== "string" || body.reason.trim().length < 5 || body.reason.trim().length > 500) return null;

  let serialized: string;
  try { serialized = JSON.stringify(body); } catch { return null; }
  if (serialized.length > 16_384) return null;

  for (const field of IDENTIFIER_FIELDS) {
    const value = body[field];
    if (value !== undefined && value !== null && value !== ""
      && (typeof value !== "string" || !UUID.test(value))) return null;
  }
  if (body.regionCode !== undefined && body.regionCode !== null && body.regionCode !== ""
    && (typeof body.regionCode !== "string" || !/^\d{6}$/.test(body.regionCode))) return null;
  for (const [key, value] of Object.entries(body)) {
    if (key === "action" || key === "reason" || value === null || value === undefined) continue;
    if (typeof value === "string" && (value.length > 2_000 || TEXT_CONTROL.test(value))) return null;
  }

  return {
    action: body.action,
    reason: body.reason.trim(),
    payload: Object.fromEntries(Object.entries(body).filter(([key]) => !["action", "reason", "actor_id", "actorId"].includes(key))),
  };
}
