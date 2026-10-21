import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../supabase", () => ({ supabase: { auth: { getSession: async () => ({ data: { session: null } }) } } }));
vi.mock("@/components/AuthProvider", () => ({ GUEST_STORAGE_KEY: "mpm_guest_mode" }));

import { baseConfig } from "../hooks";
import { ApiError } from "../errors";

type Retry = NonNullable<typeof baseConfig.onErrorRetry>;
const onErrorRetry = baseConfig.onErrorRetry as Retry;

function run(err: unknown, retryCount = 0) {
  const revalidate = vi.fn();
  onErrorRetry(err as never, "key", {} as never, revalidate as never, { retryCount, dedupe: false });
  return revalidate;
}

afterEach(() => vi.useRealTimers());

describe("SWR 재시도 정책", () => {
  it("4xx는 재시도하지 않는다", () => {
    vi.useFakeTimers();
    const revalidate = run(new ApiError(404, "없음"));
    vi.advanceTimersByTime(60_000);
    expect(revalidate).not.toHaveBeenCalled();
  });

  it("5xx는 지수 백오프로 재시도한다", () => {
    vi.useFakeTimers();
    const revalidate = run(new ApiError(500, "서버"), 0);
    vi.advanceTimersByTime(1_999);
    expect(revalidate).not.toHaveBeenCalled();
    vi.advanceTimersByTime(2);
    expect(revalidate).toHaveBeenCalledTimes(1);
  });

  it("429는 Retry-After만큼 기다린다", () => {
    vi.useFakeTimers();
    const revalidate = run(new ApiError(429, "많음", { retryAfter: 9 }), 0);
    vi.advanceTimersByTime(8_999);
    expect(revalidate).not.toHaveBeenCalled();
    vi.advanceTimersByTime(2);
    expect(revalidate).toHaveBeenCalledTimes(1);
  });

  it("세 번 실패하면 포기한다", () => {
    vi.useFakeTimers();
    const revalidate = run(new ApiError(500, "서버"), 3);
    vi.advanceTimersByTime(60_000);
    expect(revalidate).not.toHaveBeenCalled();
  });

  it("탭이 숨겨진 동안은 폴링하지 않는다", () => {
    expect(baseConfig.refreshWhenHidden).toBe(false);
  });
});
