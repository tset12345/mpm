"use client";
import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useSession } from "@/components/AuthProvider";
import type { MarketRankings, RankingStock } from "@/lib/types";

function fmtAmt(n: number): string {
  if (Math.abs(n) >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + "십억";
  if (Math.abs(n) >= 100_000_000) return (n / 100_000_000).toFixed(0) + "억";
  if (Math.abs(n) >= 10_000) return (n / 10_000).toFixed(0) + "만";
  return n.toLocaleString();
}

function fmtVol(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return n.toLocaleString();
}

function rateColor(rate: number): string {
  return rate > 0 ? "text-red-600" : rate < 0 ? "text-blue-600" : "text-gray-500";
}

function netColor(n: number): string {
  return n > 0 ? "text-red-600" : n < 0 ? "text-blue-600" : "text-gray-500";
}

type MetricRenderer = (s: RankingStock) => React.ReactNode;

function RankCard({
  title,
  items,
  metric,
  metricLabel,
}: {
  title: string;
  items: RankingStock[];
  metric: MetricRenderer;
  metricLabel: string;
}) {
  return (
    <div className="border rounded-xl overflow-hidden bg-white">
      <div className="px-4 py-2.5 bg-gray-50 border-b">
        <span className="text-sm font-semibold text-gray-700">{title}</span>
      </div>
      {items.length === 0 ? (
        <div className="px-4 py-6 text-sm text-gray-400 text-center">데이터 없음</div>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-400 border-b">
              <th className="pl-4 pr-2 py-1.5 text-left font-medium w-5">#</th>
              <th className="px-2 py-1.5 text-left font-medium">종목</th>
              <th className="px-2 py-1.5 text-right font-medium">현재가</th>
              <th className="px-2 py-1.5 text-right font-medium">등락률</th>
              <th className="pr-4 pl-2 py-1.5 text-right font-medium">{metricLabel}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((s, i) => (
              <tr key={s.stock_code} className="border-b last:border-0 hover:bg-gray-50 transition-colors">
                <td className="pl-4 pr-2 py-2 text-gray-400 tabular-nums">{i + 1}</td>
                <td className="px-2 py-2">
                  <div className="font-medium text-gray-800 leading-none">{s.stock_name}</div>
                  <div className="text-gray-400 mt-0.5">{s.stock_code}</div>
                </td>
                <td className="px-2 py-2 text-right tabular-nums text-gray-700">
                  {s.current_price.toLocaleString()}
                </td>
                <td className={`px-2 py-2 text-right tabular-nums font-medium ${rateColor(s.change_rate)}`}>
                  {s.change_rate > 0 ? "+" : ""}{s.change_rate.toFixed(2)}%
                </td>
                <td className="pr-4 pl-2 py-2 text-right tabular-nums">{metric(s)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const SECTIONS: {
  key: keyof MarketRankings;
  title: string;
  metricLabel: string;
  metric: MetricRenderer;
}[] = [
  {
    key: "rise",
    title: "상승률 상위",
    metricLabel: "거래량",
    metric: (s) => <span className="text-gray-600">{fmtVol(s.volume ?? 0)}</span>,
  },
  {
    key: "fall",
    title: "하락률 상위",
    metricLabel: "거래량",
    metric: (s) => <span className="text-gray-600">{fmtVol(s.volume ?? 0)}</span>,
  },
  {
    key: "volume",
    title: "거래량 상위",
    metricLabel: "거래량",
    metric: (s) => <span className="text-gray-600">{fmtVol(s.volume ?? 0)}</span>,
  },
  {
    key: "amount",
    title: "거래대금 상위",
    metricLabel: "거래대금",
    metric: (s) => <span className="text-gray-600">{fmtAmt(s.amount ?? 0)}</span>,
  },
  {
    key: "foreign_buy",
    title: "외국인 순매수 상위",
    metricLabel: "순매수(주)",
    metric: (s) => (
      <span className={netColor(s.net_buy ?? 0)}>
        {(s.net_buy ?? 0) > 0 ? "+" : ""}{fmtVol(s.net_buy ?? 0)}
      </span>
    ),
  },
  {
    key: "institution_buy",
    title: "기관 순매수 상위",
    metricLabel: "순매수(주)",
    metric: (s) => (
      <span className={netColor(s.net_buy ?? 0)}>
        {(s.net_buy ?? 0) > 0 ? "+" : ""}{fmtVol(s.net_buy ?? 0)}
      </span>
    ),
  },
  {
    key: "high_52w",
    title: "52주 신고가",
    metricLabel: "52주 고가",
    metric: (s) => <span className="text-gray-600">{(s.high_52w ?? 0).toLocaleString()}</span>,
  },
  {
    key: "low_52w",
    title: "52주 신저가",
    metricLabel: "52주 저가",
    metric: (s) => <span className="text-gray-600">{(s.low_52w ?? 0).toLocaleString()}</span>,
  },
];

export default function MarketRankings() {
  const session = useSession();
  const [rankings, setRankings] = useState<MarketRankings | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    setFetchError(null);
    try {
      const res = await api.getMarketRankings(5);
      setRankings(res.data ?? null);
      setFetchedAt(new Date());
    } catch (err: unknown) {
      setFetchError(err instanceof Error ? err.message : "데이터 조회 실패");
    } finally {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="space-y-4">
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

      {loading && !rankings ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="rounded-xl border bg-gray-50 h-44 animate-pulse" />
          ))}
        </div>
      ) : rankings ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {SECTIONS.map(({ key, title, metricLabel, metric }) => (
            <RankCard
              key={key}
              title={title}
              items={rankings[key]}
              metricLabel={metricLabel}
              metric={metric}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
