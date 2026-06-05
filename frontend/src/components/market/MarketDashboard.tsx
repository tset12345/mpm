"use client";
import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useSession } from "@/components/AuthProvider";
import type { MarketIndices, MarketIndexItem, InvestorTrend } from "@/lib/types";

function fmtNum(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 100000) return (n / 100000).toFixed(1) + "만";
  if (abs >= 10000) return (n / 10000).toFixed(1) + "천";
  return n.toLocaleString();
}

function signColor(sign: string, type: "text" | "bg" = "text"): string {
  const up = sign === "1" || sign === "2";
  const dn = sign === "4" || sign === "5";
  if (type === "bg") return up ? "bg-red-50" : dn ? "bg-blue-50" : "bg-gray-50";
  return up ? "text-red-600" : dn ? "text-blue-600" : "text-gray-500";
}

function IndexCard({
  item,
  prefix = "",
  suffix = "",
  decimals = 2,
}: {
  item: MarketIndexItem;
  prefix?: string;
  suffix?: string;
  decimals?: number;
}) {
  const up = item.sign === "1" || item.sign === "2";
  const dn = item.sign === "4" || item.sign === "5";
  const arrow = up ? "▲" : dn ? "▼" : "─";
  const color = signColor(item.sign);

  return (
    <div className={`rounded-xl border p-3.5 ${signColor(item.sign, "bg")}`}>
      <div className="text-xs font-semibold text-gray-500 mb-2">{item.label}</div>
      {item.price == null ? (
        <div className="text-sm text-gray-400">조회 실패</div>
      ) : (
        <>
          <div className="text-xl font-bold tabular-nums text-gray-900 leading-tight">
            {prefix}
            {item.price.toLocaleString(undefined, {
              minimumFractionDigits: decimals,
              maximumFractionDigits: decimals,
            })}
            {suffix}
          </div>
          <div className={`mt-1 text-xs font-medium tabular-nums ${color}`}>
            {arrow}{" "}
            {item.change != null &&
              Math.abs(item.change).toLocaleString(undefined, {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals,
              })}
            {suffix}
            {item.change_rate != null && (
              <span className="ml-1.5 opacity-75">
                ({item.change_rate > 0 ? "+" : ""}
                {item.change_rate.toFixed(2)}%)
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}

const SECTIONS: {
  title: string;
  keys: (keyof MarketIndices)[];
  cfg: Record<string, { prefix?: string; suffix?: string; decimals?: number }>;
}[] = [
  {
    title: "국내 지수",
    keys: ["kospi", "kosdaq"],
    cfg: {},
  },
  {
    title: "미국 지수",
    keys: ["nasdaq", "dow", "sp500"],
    cfg: {},
  },
  {
    title: "환율 · 원자재 · 금리",
    keys: ["usd_krw", "crude_oil", "us10y"],
    cfg: {
      crude_oil: { prefix: "$" },
      us10y: { suffix: "%" },
    },
  },
];

export default function MarketDashboard() {
  const session = useSession();
  const [indices, setIndices] = useState<MarketIndices | null>(null);
  const [investor, setInvestor] = useState<InvestorTrend | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    setFetchError(null);
    try {
      const [idxRes, invRes] = await Promise.all([
        api.getMarketIndices(),
        api.getInvestorTrend(),
      ]);
      setIndices(idxRes.data ?? null);
      setInvestor(invRes.data ?? null);
      setFetchedAt(new Date());
    } catch (err: unknown) {
      setFetchError(err instanceof Error ? err.message : "데이터 조회 실패");
    } finally {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="space-y-5">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="text-xs text-gray-400">
          {fetchedAt ? `기준: ${fetchedAt.toLocaleTimeString("ko-KR")}` : ""}
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="text-xs text-blue-500 hover:underline disabled:opacity-40"
        >
          {loading ? "조회 중..." : "새로고침"}
        </button>
      </div>

      {fetchError && (
        <div className="text-sm text-red-500 bg-red-50 rounded-lg px-4 py-3">{fetchError}</div>
      )}

      {/* 지수 섹션 */}
      {indices
        ? SECTIONS.map(({ title, keys, cfg }) => (
            <div key={title}>
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                {title}
              </div>
              <div className={`grid gap-3 grid-cols-2 ${keys.length >= 3 ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}>
                {keys.map((k) => {
                  const item = indices[k];
                  const { prefix = "", suffix = "", decimals = 2 } = cfg[k as string] ?? {};
                  return (
                    <IndexCard
                      key={k}
                      item={item}
                      prefix={prefix}
                      suffix={suffix}
                      decimals={decimals}
                    />
                  );
                })}
              </div>
            </div>
          ))
        : loading && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="rounded-xl border bg-gray-50 p-4 h-20 animate-pulse" />
              ))}
            </div>
          )}

      {/* 수급 현황 */}
      {investor && (
        <div>
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
            수급 현황 (상위 50종목)
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "외국인 순매수", value: investor.foreign_net_buy },
              { label: "기관 순매수", value: investor.institution_net_buy },
              { label: "개인 순매수", value: investor.individual_net_buy },
            ].map(({ label, value }) => {
              const sign = value > 0 ? "2" : value < 0 ? "4" : "3";
              return (
                <div key={label} className={`rounded-xl border p-3.5 text-center ${signColor(sign, "bg")}`}>
                  <div className="text-xs text-gray-500 mb-1">{label}</div>
                  <div className={`text-base font-bold tabular-nums ${signColor(sign)}`}>
                    {value > 0 ? "+" : ""}
                    {fmtNum(value)}주
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
