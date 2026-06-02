"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { VirtualAccount, VirtualPosition, VirtualTrade, VirtualPerformance } from "@/lib/types";

// ── 유틸 ─────────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, digits = 0) {
  if (n == null) return "—";
  return n.toLocaleString("ko-KR", { maximumFractionDigits: digits });
}

function pct(n: number | null | undefined) {
  if (n == null) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function colorPct(n: number | null | undefined) {
  if (n == null) return "text-gray-400";
  return n > 0 ? "text-red-600" : n < 0 ? "text-blue-600" : "text-gray-500";
}

const STRATEGY_LABEL: Record<string, string> = {
  engine_a: "Engine A (추세)",
  engine_b: "Engine B (역추세)",
  both: "전체",
};

const TRIGGER_LABEL: Record<string, string> = {
  algo_buy:    "알고리즘 매수",
  stop_loss:   "손절",
  take_profit: "익절",
  sell_signal: "매도신호",
  manual:      "수동",
};

// ── 성과 카드 ─────────────────────────────────────────────────────────────────

function PerformanceCard({ perf }: { perf: VirtualPerformance }) {
  const returnColor = perf.total_return_rate >= 0 ? "text-red-600" : "text-blue-600";
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
      <div className="bg-white rounded-xl border p-3">
        <div className="text-[11px] text-gray-400 mb-1">총 평가금액</div>
        <div className="text-base font-bold text-gray-800">{fmt(perf.total_value)}원</div>
        <div className={`text-xs font-semibold mt-0.5 ${returnColor}`}>{pct(perf.total_return_rate)}</div>
      </div>
      <div className="bg-white rounded-xl border p-3">
        <div className="text-[11px] text-gray-400 mb-1">실현 손익</div>
        <div className={`text-base font-bold ${colorPct(perf.realized_pnl)}`}>{fmt(perf.realized_pnl)}원</div>
        <div className="text-[11px] text-gray-400 mt-0.5">미실현 {fmt(perf.unrealized_pnl)}원</div>
      </div>
      <div className="bg-white rounded-xl border p-3">
        <div className="text-[11px] text-gray-400 mb-1">승률</div>
        <div className="text-base font-bold text-gray-800">
          {perf.win_rate != null ? `${perf.win_rate.toFixed(1)}%` : "—"}
        </div>
        <div className="text-[11px] text-gray-400 mt-0.5">매도 {perf.sell_count}회</div>
      </div>
      <div className="bg-white rounded-xl border p-3">
        <div className="text-[11px] text-gray-400 mb-1">최대 낙폭</div>
        <div className="text-base font-bold text-blue-600">
          {perf.max_drawdown != null ? `${perf.max_drawdown.toFixed(2)}%` : "—"}
        </div>
        <div className="text-[11px] text-gray-400 mt-0.5">
          평균 보유 {perf.avg_hold_days != null ? `${perf.avg_hold_days}일` : "—"}
        </div>
      </div>
    </div>
  );
}

// ── 포지션 테이블 ─────────────────────────────────────────────────────────────

function PositionTable({ positions }: { positions: VirtualPosition[] }) {
  if (!positions.length)
    return <p className="text-sm text-gray-400 py-6 text-center">보유 포지션 없음</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[11px] text-gray-400 border-b">
            <th className="text-left py-2 pr-3 font-medium">종목</th>
            <th className="text-right py-2 px-2 font-medium">수량</th>
            <th className="text-right py-2 px-2 font-medium">평균가</th>
            <th className="text-right py-2 px-2 font-medium">현재가</th>
            <th className="text-right py-2 px-2 font-medium">손익</th>
            <th className="text-right py-2 px-2 font-medium">수익률</th>
            <th className="text-right py-2 pl-2 font-medium">보유일</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => (
            <tr key={p.id} className="border-b last:border-0 hover:bg-gray-50">
              <td className="py-2 pr-3">
                <div className="font-medium text-gray-800">{p.stock_name}</div>
                <div className="text-[11px] text-gray-400 flex items-center gap-1">
                  {p.stock_code}
                  {p.engine && (
                    <span className={`px-1 rounded text-[10px] font-bold ${
                      p.engine === "A" ? "bg-orange-100 text-orange-700" : "bg-sky-100 text-sky-700"
                    }`}>
                      {p.engine === "A" ? "⬆ A" : "↩ B"}
                    </span>
                  )}
                </div>
              </td>
              <td className="text-right py-2 px-2 font-mono">{fmt(p.quantity)}</td>
              <td className="text-right py-2 px-2 font-mono">{fmt(p.avg_price)}</td>
              <td className="text-right py-2 px-2 font-mono">{fmt(p.current_price)}</td>
              <td className={`text-right py-2 px-2 font-mono font-semibold ${colorPct(p.profit_loss)}`}>
                {p.profit_loss != null ? `${p.profit_loss >= 0 ? "+" : ""}${fmt(p.profit_loss)}` : "—"}
              </td>
              <td className={`text-right py-2 px-2 font-semibold ${colorPct(p.profit_rate)}`}>
                {pct(p.profit_rate)}
              </td>
              <td className="text-right py-2 pl-2 text-gray-500">
                {p.hold_days != null ? `${p.hold_days}일` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── 체결 내역 테이블 ──────────────────────────────────────────────────────────

function TradeTable({ trades }: { trades: VirtualTrade[] }) {
  if (!trades.length)
    return <p className="text-sm text-gray-400 py-6 text-center">체결 내역 없음</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[11px] text-gray-400 border-b">
            <th className="text-left py-2 pr-3 font-medium">날짜</th>
            <th className="text-left py-2 pr-3 font-medium">종목</th>
            <th className="text-center py-2 px-2 font-medium">구분</th>
            <th className="text-right py-2 px-2 font-medium">체결가</th>
            <th className="text-right py-2 px-2 font-medium">수량</th>
            <th className="text-right py-2 px-2 font-medium">금액</th>
            <th className="text-left py-2 px-2 font-medium">트리거</th>
            <th className="text-right py-2 pl-2 font-medium">손익</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="border-b last:border-0 hover:bg-gray-50">
              <td className="py-2 pr-3 text-gray-500 text-[12px]">{t.traded_at}</td>
              <td className="py-2 pr-3">
                <div className="font-medium text-gray-800">{t.stock_name}</div>
                <div className="text-[11px] text-gray-400">{t.stock_code}</div>
              </td>
              <td className="text-center py-2 px-2">
                <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                  t.side === "buy" ? "bg-red-50 text-red-600" : "bg-blue-50 text-blue-600"
                }`}>
                  {t.side === "buy" ? "매수" : "매도"}
                </span>
              </td>
              <td className="text-right py-2 px-2 font-mono">{fmt(t.price)}</td>
              <td className="text-right py-2 px-2 font-mono">{fmt(t.quantity)}</td>
              <td className="text-right py-2 px-2 font-mono text-gray-600">{fmt(t.amount)}</td>
              <td className="py-2 px-2">
                <span className="text-[11px] text-gray-500">{TRIGGER_LABEL[t.trigger_type] ?? t.trigger_type}</span>
              </td>
              <td className={`text-right py-2 pl-2 font-mono font-semibold ${colorPct(t.pnl)}`}>
                {t.pnl != null ? `${t.pnl >= 0 ? "+" : ""}${fmt(t.pnl)}` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── 계좌 생성 모달 ────────────────────────────────────────────────────────────

function CreateAccountModal({ onClose, onCreate }: {
  onClose: () => void;
  onCreate: (account: VirtualAccount) => void;
}) {
  const [form, setForm] = useState({
    name: "가상 계좌 1",
    initial_cash: 10000000,
    strategy: "both",
    min_score: 50,
    max_positions: 5,
    position_size: 20,
    stop_loss_pct: 10,
    take_profit_pct: 20,
  });
  const [loading, setLoading] = useState(false);

  const handle = (k: string, v: string | number) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    setLoading(true);
    try {
      const res = await api.createVirtualAccount(form);
      onCreate(res.data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-xl">
        <h2 className="text-base font-bold text-gray-800 mb-4">가상 계좌 생성</h2>
        <div className="space-y-3 text-sm">
          <label className="block">
            <span className="text-gray-500 text-xs">계좌명</span>
            <input className="w-full mt-1 border rounded-lg px-3 py-2 text-sm" value={form.name}
              onChange={(e) => handle("name", e.target.value)} />
          </label>
          <label className="block">
            <span className="text-gray-500 text-xs">초기 시드 (원)</span>
            <input className="w-full mt-1 border rounded-lg px-3 py-2 text-sm font-mono" type="number"
              value={form.initial_cash} onChange={(e) => handle("initial_cash", Number(e.target.value))} />
          </label>
          <label className="block">
            <span className="text-gray-500 text-xs">전략</span>
            <select className="w-full mt-1 border rounded-lg px-3 py-2 text-sm"
              value={form.strategy} onChange={(e) => handle("strategy", e.target.value)}>
              <option value="both">전체 (A + B)</option>
              <option value="engine_a">Engine A — 추세 돌파형</option>
              <option value="engine_b">Engine B — 역추세 반등형</option>
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            {[
              ["최소 기술 점수", "min_score"],
              ["최대 보유 종목", "max_positions"],
              ["종목당 투자 비율 (%)", "position_size"],
              ["손절 기준 (%)", "stop_loss_pct"],
              ["익절 기준 (%)", "take_profit_pct"],
            ].map(([label, key]) => (
              <label key={key} className="block">
                <span className="text-gray-500 text-xs">{label}</span>
                <input className="w-full mt-1 border rounded-lg px-3 py-2 text-sm font-mono" type="number"
                  value={form[key as keyof typeof form]}
                  onChange={(e) => handle(key, Number(e.target.value))} />
              </label>
            ))}
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button onClick={onClose}
            className="flex-1 border rounded-lg py-2 text-sm text-gray-600 hover:bg-gray-50">
            취소
          </button>
          <button onClick={submit} disabled={loading}
            className="flex-1 bg-gray-800 text-white rounded-lg py-2 text-sm font-semibold hover:bg-gray-700 disabled:opacity-50">
            {loading ? "생성 중..." : "생성"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── 메인 페이지 ───────────────────────────────────────────────────────────────

export default function VirtualPage() {
  const [accounts, setAccounts] = useState<VirtualAccount[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [positions, setPositions] = useState<VirtualPosition[]>([]);
  const [trades, setTrades] = useState<VirtualTrade[]>([]);
  const [perf, setPerf] = useState<VirtualPerformance | null>(null);
  const [tab, setTab] = useState<"positions" | "trades">("positions");
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);

  const selected = accounts.find((a) => a.id === selectedId) ?? null;

  const loadAccounts = useCallback(async () => {
    try {
      const res = await api.getVirtualAccounts();
      setAccounts(res.data);
      if (res.data.length > 0 && selectedId == null) {
        setSelectedId(res.data[0].id);
      }
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  const loadDetail = useCallback(async (id: number) => {
    const [posRes, tradeRes, perfRes] = await Promise.all([
      api.getVirtualPositions(id),
      api.getVirtualTrades(id),
      api.getVirtualPerformance(id),
    ]);
    setPositions(posRes.data);
    setTrades(tradeRes.data);
    setPerf(perfRes.data);
  }, []);

  useEffect(() => { loadAccounts(); }, []);
  useEffect(() => { if (selectedId) loadDetail(selectedId); }, [selectedId]);

  const deleteAccount = async (id: number) => {
    if (!confirm("계좌를 삭제하시겠습니까? 모든 포지션과 체결 내역이 삭제됩니다.")) return;
    await api.deleteVirtualAccount(id);
    const next = accounts.filter((a) => a.id !== id);
    setAccounts(next);
    setSelectedId(next[0]?.id ?? null);
  };

  const toggleActive = async (account: VirtualAccount) => {
    const res = await api.updateVirtualAccount(account.id, { is_active: !account.is_active });
    setAccounts((prev) => prev.map((a) => a.id === account.id ? res.data : a));
  };

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen text-gray-400 text-sm">로딩 중...</div>;
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-bold text-gray-800">가상 거래</h1>
          <p className="text-xs text-gray-400 mt-0.5">알고리즘 기반 페이퍼 트레이딩</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="bg-gray-800 text-white text-sm px-4 py-2 rounded-xl font-semibold hover:bg-gray-700">
          + 계좌 생성
        </button>
      </div>

      {accounts.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p className="text-sm">가상 계좌가 없습니다.</p>
          <button onClick={() => setShowCreate(true)}
            className="mt-3 text-sm text-gray-600 underline">
            첫 번째 계좌 만들기
          </button>
        </div>
      ) : (
        <>
          {/* 계좌 탭 선택 */}
          <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
            {accounts.map((a) => (
              <button key={a.id}
                onClick={() => setSelectedId(a.id)}
                className={`flex-shrink-0 px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${
                  a.id === selectedId
                    ? "bg-gray-800 text-white border-gray-800"
                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                }`}>
                <span>{a.name}</span>
                {!a.is_active && <span className="ml-1 text-[10px] opacity-60">(정지)</span>}
              </button>
            ))}
          </div>

          {selected && (
            <>
              {/* 계좌 요약 바 */}
              <div className="bg-white rounded-xl border px-4 py-3 mb-4 flex flex-wrap items-center gap-4">
                <div>
                  <span className="text-[11px] text-gray-400">전략 </span>
                  <span className="text-xs font-semibold text-gray-700">{STRATEGY_LABEL[selected.strategy]}</span>
                </div>
                <div>
                  <span className="text-[11px] text-gray-400">잔액 </span>
                  <span className="text-xs font-semibold font-mono text-gray-700">{fmt(selected.current_cash)}원</span>
                </div>
                <div>
                  <span className="text-[11px] text-gray-400">최소점수 </span>
                  <span className="text-xs font-semibold text-gray-700">{selected.min_score}점</span>
                </div>
                <div>
                  <span className="text-[11px] text-gray-400">손절 </span>
                  <span className="text-xs font-semibold text-blue-600">-{selected.stop_loss_pct}%</span>
                  <span className="text-[11px] text-gray-400 ml-2">익절 </span>
                  <span className="text-xs font-semibold text-red-600">+{selected.take_profit_pct}%</span>
                </div>
                <div className="ml-auto flex gap-2">
                  <button onClick={() => toggleActive(selected)}
                    className="text-xs px-3 py-1 rounded-lg border text-gray-500 hover:bg-gray-50">
                    {selected.is_active ? "정지" : "활성화"}
                  </button>
                  <button onClick={() => deleteAccount(selected.id)}
                    className="text-xs px-3 py-1 rounded-lg border border-red-200 text-red-400 hover:bg-red-50">
                    삭제
                  </button>
                </div>
              </div>

              {/* 성과 카드 */}
              {perf && <PerformanceCard perf={perf} />}

              {/* 탭 */}
              <div className="flex gap-3 mb-3 border-b">
                {(["positions", "trades"] as const).map((t) => (
                  <button key={t} onClick={() => setTab(t)}
                    className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
                      tab === t ? "border-gray-800 text-gray-800" : "border-transparent text-gray-400 hover:text-gray-600"
                    }`}>
                    {t === "positions" ? `보유 포지션 (${positions.length})` : `체결 내역 (${trades.length})`}
                  </button>
                ))}
              </div>

              <div className="bg-white rounded-xl border p-4">
                {tab === "positions"
                  ? <PositionTable positions={positions} />
                  : <TradeTable trades={trades} />
                }
              </div>
            </>
          )}
        </>
      )}

      {showCreate && (
        <CreateAccountModal
          onClose={() => setShowCreate(false)}
          onCreate={(account) => {
            setAccounts((prev) => [...prev, account]);
            setSelectedId(account.id);
            setShowCreate(false);
          }}
        />
      )}
    </main>
  );
}
