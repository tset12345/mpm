import { describe, expect, it } from "vitest";
import { formatVersion } from "../version";

describe("formatVersion", () => {
  it("버전과 커밋을 함께 표시한다", () => {
    expect(formatVersion("2.0.0", "abc1234")).toBe("v2.0.0 · abc1234");
  });

  it("커밋을 모르면 버전만 표시한다", () => {
    expect(formatVersion("2.0.0", "")).toBe("v2.0.0");
  });

  it("버전이 없으면 표시하지 않는다", () => {
    expect(formatVersion("", "abc1234")).toBeNull();
  });
});
