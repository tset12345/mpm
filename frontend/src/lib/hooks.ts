"use client";

import useSWR, { type SWRConfiguration } from "swr";
import { api } from "./api";
import { ApiError } from "./errors";

/**
 * 읽기 전용 조회용 SWR 훅 모음.
 * - 같은 키의 요청은 컴포넌트 수와 상관없이 하나로 합쳐진다 (dedupe).
 * - 탭이 보이지 않으면 폴링을 멈추고, 다시 보이면 한 번 갱신한다.
 * - 4xx(401·403·404 등)는 재시도하지 않고, 429는 Retry-After를 지켜 재시도한다.
 */
export const baseConfig: SWRConfiguration = {
  dedupingInterval: 5_000,
  focusThrottleInterval: 30_000,
  revalidateOnFocus: true,
  revalidateOnReconnect: true,
  keepPreviousData: true,
  refreshWhenHidden: false,
  errorRetryCount: 3,
  onErrorRetry: (err, _key, _config, revalidate, { retryCount }) => {
    if (err instanceof ApiError && !err.retryable) return;
    if (retryCount >= 3) return;
    const waitMs = err instanceof ApiError && err.retryAfter
      ? err.retryAfter * 1000
      : Math.min(2_000 * 2 ** retryCount, 15_000);
    setTimeout(() => revalidate({ retryCount }), waitMs);
  },
};

export function useMarketIndices(opts: SWRConfiguration = {}) {
  return useSWR("market:indices", () => api.getMarketIndices(), { ...baseConfig, refreshInterval: 60_000, ...opts });
}

export function useInvestorTrend(opts: SWRConfiguration = {}) {
  return useSWR("market:investor", () => api.getInvestorTrend(), { ...baseConfig, refreshInterval: 60_000, ...opts });
}

export function useMarketRankings(limit = 5, opts: SWRConfiguration = {}) {
  return useSWR(["market:rankings", limit], () => api.getMarketRankings(limit), {
    ...baseConfig, refreshInterval: 120_000, ...opts,
  });
}

export function useTreemap(sort: "change_rate" | "frgn_net_buy" | "org_net_buy", opts: SWRConfiguration = {}) {
  return useSWR(["market:treemap", sort], () => api.getMarketTreemap(sort), {
    ...baseConfig, refreshInterval: 180_000, ...opts,
  });
}

/** 추천 종목 현재가·등락률 폴링. enabled가 false면 요청하지 않는다. */
export function useRecommendationPrices(enabled: boolean, opts: SWRConfiguration = {}) {
  return useSWR(enabled ? "stocks:recommend-prices" : null, () => api.getRecommendationPrices(), {
    ...baseConfig, refreshInterval: 30_000, ...opts,
  });
}
