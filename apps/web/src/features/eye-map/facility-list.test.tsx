import { describe, expect, it } from "vitest";
import { formatDistance } from "./facility-list";

describe("formatDistance", () => {
  it("uses rounded meters below one kilometer and one decimal kilometers above it", () => {
    expect(formatDistance(620)).toBe("620 m");
    expect(formatDistance(999.6)).toBe("1000 m");
    expect(formatDistance(3_420)).toBe("3.4 km");
  });
});
