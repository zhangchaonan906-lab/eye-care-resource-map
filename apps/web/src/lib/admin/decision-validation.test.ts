import { describe, expect, it } from "vitest";
import { validateAdminDecisionInput } from "./decision-validation";

describe("validateAdminDecisionInput", () => {
  it("rejects SQL-shaped action names before the database boundary", () => {
    expect(validateAdminDecisionInput("facility", {
      action: "PUBLISH; DROP TABLE facilities; --",
      reason: "synthetic integration test",
    })).toBeNull();
  });

  it("rejects malformed candidate and facility identifiers in decision payloads", () => {
    expect(validateAdminDecisionInput("duplicate", {
      action: "MERGE", reason: "synthetic integration test", targetFacilityId: "' OR 1=1 --",
    })).toBeNull();
  });

  it("accepts an omitted region for merging into an existing facility", () => {
    expect(validateAdminDecisionInput("duplicate", {
      action: "MERGE", reason: "synthetic integration test", targetFacilityId: "00000000-0000-4000-8000-000000000001",
      primaryCandidateId: "", regionCode: "",
    })).not.toBeNull();
  });

  it("rejects oversized decision values without rejecting safe HTML text for escaping", () => {
    expect(validateAdminDecisionInput("candidate", {
      action: "CREATE_FACILITY", reason: "synthetic integration test", name: "x".repeat(2_001),
    })).toBeNull();
    expect(validateAdminDecisionInput("candidate", {
      action: "CREATE_FACILITY", reason: "synthetic integration test", name: "<img onerror=alert(1)>",
    })).not.toBeNull();
  });
});
