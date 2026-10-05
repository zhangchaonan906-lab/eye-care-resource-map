import { describe, expect, it } from "vitest";
import { parseCorrectionInput } from "./validation";

describe("correction input", () => {
  it("accepts only bounded minimal reports", () => {
    expect(parseCorrectionInput({ type: "moved", description: "新地址为测试路 1 号" })).toEqual({
      type: "moved", description: "新地址为测试路 1 号",
    });
  });
  it.each([
    [{ type: "other", description: "描述足够长" }],
    [{ type: "closed", description: "太短" }],
    [{ type: "closed", description: "x".repeat(1001) }],
    [{ type: "closed", description: "描述足够长", facilityId: "not-a-uuid" }],
    [null],
  ])("rejects invalid or oversized reports %#", (input) => expect(parseCorrectionInput(input)).toBeNull());
});
