"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { createChart, IChartApi, ISeriesApi, LineData } from "lightweight-charts";
import { api } from "@/lib/api";
import { useSession } from "@/components/AuthProvider";
import { IndexCandle, AdrPoint, InvestorTrend } from "@/lib/types";

type Market = "KOSPI" | "KOSDAQ";
type Period = "D" | "W" | "M";

const CHART_OPTIONS = {
  layout: { background: { color: "#ffffff" }, textColor: "#374151" },
  grid: { vertLines: { color: "#f3f4f6" }, horzLines: { color: "#f3f4f6" } },
  rightPriceScale: { borderColor: "#e5e7eb" },
  timeScale: { borderColor: "#e5e7eb", timeVisible: false },
} as const;

function computeMA(candles: IndexCandle[], period: number): LineData[] {
  const result: LineData[] = [];
  for (let i = period - 1; i < candles.length; i++) {
    const sum = candles.slice(i - period + 1, i + 1).reduce((s, d) => s + d.close, 0);
    result.push({ time: candles[i].date as import("lightweight-charts").Time, value: sum / period });
  }
  return result;
}

function fmtNum(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 100000) return (n / 100000).toFixed(1) + "만";
  if (abs >= 10000) return (n / 10000).toFixed(1) + "천";
  return n.toLocaleString();
}

export default function MarketDashboard() {
  const session = useSession();
  const [market, setMarket] = useState<Market>("KOSPI");
  const [period, setPeriod] = useState<Period>("D");
  const [maOn, setMaOn] = useState({ ma20: true, ma60: true, ma120: false });
  const [candles, setCandles] = useState<IndexCandle[]>([]);
  const [adrData, setAdrData] = useState<AdrPoint[]>([]);
  const [investor, setInvestor] = useState<InvestorTrend | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const mainRef = useRef<HTMLDivElement>(null);
  const adrRef = useRef<HTMLDivElement>(null);
  const mainChart = useRef<IChartApi | null>(null);
  const adrChart = useRef<IChartApi | null>(null);
  const syncing = useRef(false);

  const fetchData = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    setFetchError(null);
    try {
      const [chartRes, adrRes, invRes] = await Promise.all([
        api.getIndexChart(market, period),
        api.getAdr(period === "D" ? 60 : period === "W" ? 52 : 36),
        api.getInvestorTrend(),
      ]);
      setCandles(chartRes.data || []);
      setAdrData(adrRes.data || []);
      setInvestor(invRes.data);
    } catch (err: unknown) {
      setFetchError(err instanceof Error ? err.message : "데이터 조회 실패");
    } finally {
      setLoading(false);
    }
  }, [market, period, session]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Build main chart
  useEffect(() => {
    if (!mainRef.current || candles.length === 0) return;
    mainChart.current?.remove();

    const chart = createChart(mainRef.current, { ...CHART_OPTIONS, height: 320 });
    mainChart.current = chart;

    const mainSeries = chart.addLineSeries({ color: "#2563eb", lineWidth: 2, priceFormat: { type: "price", minMove: 0.01 } });
    mainSeries.setData(candles.map(c => ({ time: c.date as import("lightweight-charts").Time, value: c.close })));

    const maColors = { ma20: "#f59e0b", ma60: "#10b981", ma120: "#8b5cf6" };
    const maPeriods: [keyof typeof maOn, number][] = [["ma20", 20], ["ma60", 60], ["ma120", 120]];
    for (const [key, p] of maPeriods) {
      if (!maOn[key]) continue;
      const data = computeMA(candles, p);
      if (data.length === 0) continue;
      const s = chart.addLineSeries({ color: maColors[key], lineWidth: 1, lineStyle: 2 });
      s.setData(data);
    }

    chart.timeScale().fitContent();

    // Sync ADR
    chart.timeScale().subscribeVisibleTimeRangeChange((range) => {
      if (syncing.current || !range || !adrChart.current) return;
      syncing.current = true;
      adrChart.current.timeScale().setVisibleRange(range);
      syncing.current = false;
    });

    return () => { chart.remove(); mainChart.current = null; };
  }, [candles, maOn]);

  // Build ADR chart
  useEffect(() => {
    if (!adrRef.current || adrData.length === 0) return;
    adrChart.current?.remove();

    const chart = createChart(adrRef.current, { ...CHART_OPTIONS, height: 100 });
    adrChart.current = chart;

    const adrSeries = chart.addLineSeries({ color: "#10b981", lineWidth: 2, priceFormat: { type: "custom", minMove: 0.1, formatter: (v: number) => `${v}%` } });
    adrSeries.setData(adrData.map(d => ({ time: d.date as import("lightweight-charts").Time, value: d.adr })));

    // Reference line at 50%
    adrSeries.createPriceLine({ price: 50, color: "#9ca3af", lineWidth: 1, lineStyle: 1, axisLabelVisible: false });

    chart.timeScale().fitContent();

    chart.timeScale().subscribeVisibleTimeRangeChange((range) => {
      if (syncing.current || !range || !mainChart.current) return;
      syncing.current = true;
      mainChart.current.timeScale().setVisibleRange(range);
      syncing.current = false;
    });

    return () => { chart.remove(); adrChart.current = null; };
  }, [adrData]);

  const toggleMA = (key: keyof typeof maOn) => {
    setMaOn(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const trendColor = (n: number) => n > 0 ? "text-red-600" : n < 0 ? "text-blue-600" : "text-gray-500";
  const trendSign = (n: number) => n > 0 ? "+" : "";

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Market toggle */}
        <div className="flex rounded-lg border overflow-hidden text-sm">
          {(["KOSPI", "KOSDAQ"] as Market[]).map(m => (
            <button key={m} onClick={() => setMarket(m)}
              className={`px-3 py-1.5 ${market === m ? "bg-blue-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}>
              {m}
            </button>
          ))}
        </div>

        {/* Period toggle */}
        <div className="flex rounded-lg border overflow-hidden text-sm">
          {([["D", "일봉"], ["W", "주봉"], ["M", "월봉"]] as [Period, string][]).map(([p, label]) => (
            <button key={p} onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 ${period === p ? "bg-blue-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}>
              {label}
            </button>
          ))}
        </div>

        {/* MA toggles */}
        <div className="flex items-center gap-2 text-xs">
          {([["ma20", "MA20", "text-amber-500"], ["ma60", "MA60", "text-emerald-500"], ["ma120", "MA120", "text-violet-500"]] as [keyof typeof maOn, string, string][]).map(([key, label, color]) => (
            <button key={key} onClick={() => toggleMA(key)}
              className={`flex items-center gap-1 px-2 py-1 rounded border ${maOn[key] ? "border-current opacity-100" : "opacity-40"} ${color}`}>
              <span className={`w-3 h-0.5 inline-block ${maOn[key] ? "bg-current" : "bg-gray-300"}`} />
              {label}
            </button>
          ))}
        </div>

        {loading && <span className="text-xs text-gray-400 animate-pulse">로딩 중...</span>}
      </div>

      {/* Investor trend panel */}
      {investor && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "외국인 순매수", value: investor.foreign_net_buy },
            { label: "기관 순매수", value: investor.institution_net_buy },
            { label: "개인 순매수", value: investor.individual_net_buy },
          ].map(({ label, value }) => (
            <div key={label} className="bg-gray-50 rounded-lg p-3 text-center">
              <div className="text-xs text-gray-500 mb-1">{label}</div>
              <div className={`text-base font-bold tabular-nums ${trendColor(value)}`}>
                {trendSign(value)}{fmtNum(value)}주
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Main chart */}
      <div className="border rounded-lg overflow-hidden bg-white">
        <div className="px-3 py-2 border-b bg-gray-50 text-xs text-gray-500 font-medium">
          {market} 지수
        </div>
        {fetchError ? (
          <div className="h-80 flex flex-col items-center justify-center gap-2">
            <div className="text-red-500 text-sm">{fetchError}</div>
            <button onClick={fetchData} className="text-xs text-blue-500 underline">재시도</button>
          </div>
        ) : candles.length === 0 && !loading ? (
          <div className="h-80 flex items-center justify-center text-gray-400 text-sm">
            데이터를 불러올 수 없습니다 (KIS 지수 API 응답 없음)
          </div>
        ) : (
          <div ref={mainRef} />
        )}
      </div>

      {/* ADR sub-chart */}
      {adrData.length > 0 && (
        <div className="border rounded-lg overflow-hidden bg-white">
          <div className="px-3 py-2 border-b bg-gray-50 text-xs text-gray-500 font-medium">
            ADR (등락비율) — stock_ohlcv 종목 기준
          </div>
          <div ref={adrRef} />
        </div>
      )}
    </div>
  );
}
