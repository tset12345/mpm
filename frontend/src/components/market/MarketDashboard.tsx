"use client";
import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useSession } from "@/components/AuthProvider";
import { MarketIndices, MarketIndexItem, InvestorTrend } from "@/lib/types";

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

function IndexCard({ item, priceDecimals = 2 }: { item: MarketIndexItem; priceDecimals?: number }) {
  const up = item.sign === "1" || item.sign === "2";
  const dn = item.sign === "4" || item.sign === "5";
  const arrow = up ? "▲" : dn ? "▼" : "─";
  const color = signColor(item.sign);

  return (
    <div className={`rounded-xl border p-4 ${signColor(item.sign, "bg")}`}>
      <div className="text-xs font-semibold text-gray-500 mb-2">{item.label}</div>
      {item.price == null ? (
        <div className="text-sm text-gray-400">조회 실패</div>
      ) : (
        <>
          <div className="text-2xl font-bold tabular-nums text-gray-900">
            {item.price.toLocaleString(undefined, { minimumFractionDigits: priceDecimals, maximumFractionDigits: priceDecimals })}
          </div>
          <div className={`mt-1 text-sm font-medium tabular-nums ${color}`}>
            {arrow}{" "}
            {item.change != null && Math.abs(item.change).toLocaleString(undefined, { minimumFractionDigits: priceDecimals, maximumFractionDigits: priceDecimals })}
            {item.change_rate != null && (
              <span className="ml-1.5 text-xs opacity-80">
                ({item.change_rate > 0 ? "+" : ""}{item.change_rate.toFixed(2)}%)
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}

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

      {/* 주요 지표 4개 */}
      {indices ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <IndexCard item={indices.kospi} priceDecimals={2} />
          <IndexCard item={indices.kosdaq} priceDecimals={2} />
          <IndexCard item={indices.nasdaq} priceDecimals={2} />
          <IndexCard item={indices.usd_krw} priceDecimals={2} />
        </div>
      ) : loading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="rounded-xl border bg-gray-50 p-4 h-24 animate-pulse" />
          ))}
        </div>
      ) : null}

      {/* 수급 현황 */}
      {investor && (
        <div>
          <div className="text-sm font-semibold text-gray-700 mb-2">수급 현황 (상위 50종목)</div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "외국인 순매수", value: investor.foreign_net_buy },
              { label: "기관 순매수", value: investor.institution_net_buy },
              { label: "개인 순매수", value: investor.individual_net_buy },
            ].map(({ label, value }) => {
              const sign = value > 0 ? "2" : value < 0 ? "4" : "3";
              return (
                <div key={label} className={`rounded-xl border p-4 text-center ${signColor(sign, "bg")}`}>
                  <div className="text-xs text-gray-500 mb-1">{label}</div>
                  <div className={`text-base font-bold tabular-nums ${signColor(sign)}`}>
                    {value > 0 ? "+" : ""}{fmtNum(value)}주
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
