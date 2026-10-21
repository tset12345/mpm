import { describe, expect, it } from "vitest";
import { ApiError, describeError } from "../errors";

const json = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });

describe("ApiError.fromResponse", () => {
  it("429는 Retry-After와 요청 ID를 보존하고 대기 시간을 안내한다", async () => {
    const err = await ApiError.fromResponse(
      json(429, { detail: "요청이 너무 많습니다. 12초 후 다시 시도하세요." }, { "Retry-After": "12", "X-Request-ID": "abc123" }),
    );
    expect(err.status).toBe(429);
    expect(err.retryAfter).toBe(12);
    expect(err.requestId).toBe("abc123");
    expect(err.message).toContain("12초");
    expect(err.retryable).toBe(true);
  });

  it("5xx는 서버가 준 고정 문구를 그대로 보여준다", async () => {
    const err = await ApiError.fromResponse(json(500, { detail: "추천 이력 조회에 실패했습니다." }));
    expect(err.message).toBe("추천 이력 조회에 실패했습니다.");
    expect(err.retryable).toBe(true);
  });

  it("본문이 JSON이 아니어도 상태 코드로 안내한다", async () => {
    const err = await ApiError.fromResponse(new Response("<html>Bad Gateway</html>", { status: 502 }));
    expect(err.detail).toBeNull();
    expect(err.message).toContain("서버에 문제가 발생했습니다");
  });

  it("403·404는 재시도 대상이 아니다", async () => {
    const forbidden = await ApiError.fromResponse(json(403, { detail: "게스트는 읽기 전용입니다" }));
    const missing = await ApiError.fromResponse(json(404, {}));
    expect(forbidden.message).toBe("게스트는 읽기 전용입니다");
    expect(missing.message).toBe("요청한 정보를 찾을 수 없습니다.");
    expect(forbidden.retryable).toBe(false);
    expect(missing.retryable).toBe(false);
  });

  it("Retry-After가 숫자가 아니면 무시한다", async () => {
    const err = await ApiError.fromResponse(json(429, {}, { "Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT" }));
    expect(err.retryAfter).toBeNull();
    expect(err.message).toBe("요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.");
  });
});

describe("retryable", () => {
  it.each([[0, true], [429, true], [500, true], [503, true], [400, false], [401, false], [404, false]])(
    "상태 %i → %s", (status, expected) => {
      expect(new ApiError(status, "x").retryable).toBe(expected);
    },
  );
});

describe("describeError", () => {
  it("ApiError, Error, 알 수 없는 값을 모두 문자열로 바꾼다", () => {
    expect(describeError(new ApiError(500, "서버 오류"))).toBe("서버 오류");
    expect(describeError(new Error("boom"))).toBe("boom");
    expect(describeError(undefined)).toBe("데이터를 불러오지 못했습니다.");
    expect(describeError(null, "대체 문구")).toBe("대체 문구");
  });
});
