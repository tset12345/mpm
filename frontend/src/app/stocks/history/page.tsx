"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { HistoryEntry, StockSummary } from "@/lib/types";

type PeriodType = "daily" | "weekly" | "monthly";

function periodLabel(type: PeriodType, key: string): string {
  if (type === "daily") {
    const d = new Date(key + "T00:00:00");
    return `${d.getMonth() + 1}월 ${d.getDate()}일 (${["일", "월", "화", "수", "목", "금", "토"][d.getDay()]})`;
  }
  if (type === "weekly") {
    // '2026-W20' → '2026년 20주차'
    const [year, w] = key.split("-W");
    return `${year}년 ${Number(w)}주차`;
  }
  // monthly '2026-05' → '2026년 5월'
  const [year, month] = key.split("-");
  return `${year}년 ${Number(month)}월`;
}

function ChangeRate({ v }: { v: number | null }) {
  if (v == null) return <span className="text-gray-400">-</span>;
  const cls = v > 0 ? "text-red-500" : v < 0 ? "text-blue-500" : "text-gray-500";
  return <span className={cls}>{v > 0 ? "+" : ""}{v.toFixed(2)}%</span>;
}

function StockRow({ rank, stock }: { rank: number; stock: StockSummary }) {
  return (
    <Link
      href={`/stocks/${stock.stock_code}`}
      className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors"
    >
      <span className="w-5 text-xs text-gray-400 text-right shrink-0">{rank}</span>
      <div className="flex-1 min-w-0">
        <span className="font-medium text-sm">{stock.stock_name}</span>
        <span className="ml-1.5 text-xs text-gray-400 font-mono">{stock.stock_code}</span>
      </div>
      <div className="text-right shrink-0">
        <ChangeRate v={stock.change_rate} />
      </div>
      <div className="flex gap-1 shrink-0 max-w-[160px] flex-wrap justify-end">
        {stock.tags?.slice(0, 2).map(tag => (
          <span key={tag} className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">
            {tag}
          </span>
        ))}
      </div>
    </Link>
  );
}

function PeriodCard({ entry, type }: { entry: HistoryEntry; type: PeriodType }) {
  const [open, setOpen] = useState(false);
  const label = periodLabel(type, entry.period_key);

  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(p => !p)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 text-left"
      >
        <span className="font-medium text-sm">{label}</span>
        <span className="text-xs text-gray-400">{open ? "▲" : "▼"} 상위 {entry.stocks.length}종목</span>
      </button>
      {open && (
        <div className="divide-y">
          {entry.stocks.map((s, i) => (
            <StockRow key={s.stock_code} rank={i + 1} stock={s} />
          ))}
        </div>
      )}
    </div>
  );
}

const TAB_LABELS: Record<PeriodType, string> = {
  daily: "일별 (최근 7일)",
  weekly: "주별 (최근 4주)",
  monthly: "월별 (최근 6개월)",
};

export default function HistoryPage() {
  const [tab, setTab] = useState<PeriodType>("daily");
  const [data, setData] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (type: PeriodType) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getHistory(type);
      setData(res.data);
    } catch {
      setError("데이터를 불러오지 못했습니다.");
      setData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(tab); }, [tab, load]);

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">추천 종목 히스토리</h1>

      {/* Tabs */}
      <div className="flex border-b">
        {(Object.keys(TAB_LABELS) as PeriodType[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {loading && <div className="text-center py-20 text-gray-400">불러오는 중...</div>}

      {error && <div className="text-center py-10 text-red-500">{error}</div>}

      {!loading && !error && data.length === 0 && (
        <div className="text-center py-20 text-gray-400">
          <p>저장된 히스토리가 없습니다.</p>
          <p className="text-sm mt-1">매일 16:00 KST 자동 갱신 또는 종목 페이지에서 수동 동기화하세요.</p>
        </div>
      )}

      {!loading && !error && data.length > 0 && (
        <div className="space-y-3">
          {data.map(entry => (
            <PeriodCard key={entry.period_key} entry={entry} type={tab} />
          ))}
        </div>
      )}
    </div>
  );
}
