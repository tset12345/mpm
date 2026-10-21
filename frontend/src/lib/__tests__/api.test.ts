import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../supabase", () => ({
  supabase: { auth: { getSession: async () => ({ data: { session: { access_token: "tok" } } }) } },
}));
vi.mock("@/components/AuthProvider", () => ({ GUEST_STORAGE_KEY: "mpm_guest_mode" }));

import { api } from "../api";
import { ApiError } from "../errors";

const store: Record<string, string> = {};

beforeEach(() => {
  Object.keys(store).forEach((k) => delete store[k]);
  vi.stubGlobal("window", { location: { href: "/" } });
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v; },
    removeItem: (k: string) => { delete store[k]; },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const ok = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

describe("fetchAPI (api.*)", () => {
  it("로그인 사용자는 Bearer 토큰을 보낸다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok({ status: "success", data: [] }));
    vi.stubGlobal("fetch", fetchMock);
    await api.getMarketIndices();
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer tok");
    expect(init.signal).toBeInstanceOf(AbortSignal);
  });

  it("게스트는 토큰 대신 게스트 키 헤더만 쓴다", async () => {
    store["mpm_guest_mode"] = "true";
    const fetchMock = vi.fn().mockResolvedValue(ok({ status: "success", data: [] }));
    vi.stubGlobal("fetch", fetchMock);
    await api.getMarketIndices();
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it("429 응답은 ApiError로 던지고 대기 시간을 담는다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "x" }), { status: 429, headers: { "Retry-After": "7" } }),
    ));
    const err = await api.getMarketIndices().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(429);
    expect(err.retryAfter).toBe(7);
  });

  it("네트워크 오류는 status 0의 한국어 오류가 된다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const err = await api.getMarketIndices().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
    expect(err.message).toContain("연결할 수 없습니다");
  });

  it("타임아웃(중단)은 별도 문구로 안내한다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("aborted", "AbortError")));
    const err = await api.getMarketIndices().catch((e) => e);
    expect(err.status).toBe(0);
    expect(err.message).toContain("너무 늦습니다");
  });

  it("401은 로그인 화면으로 보낸다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 401 })));
    const err = await api.getMarketIndices().catch((e) => e);
    expect(err.status).toBe(401);
    expect((globalThis as unknown as { window: { location: { href: string } } }).window.location.href).toBe("/login");
  });

  it("응답이 오지 않으면 요청을 중단한다", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn((_url: string, init: RequestInit) =>
      new Promise((_resolve, reject) => {
        init.signal!.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
      }),
    ));
    const pending = api.getMarketIndices().catch((e) => e);
    await vi.advanceTimersByTimeAsync(60_001);
    const err = await pending;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toContain("너무 늦습니다");
  });
});
