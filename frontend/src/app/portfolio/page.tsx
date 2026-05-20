"use client";
import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Holding, HoldingSummary, SellAnalysis, PortfolioAnalysis } from "@/lib/types";
import { useProfile } from "@/hooks/useProfile";
import Link from "next/link";
import { Pencil, Trash2, Plus, Check, X, TrendingDown, ChevronUp, ChevronDown } from "lucide-react";

const PIE_COLORS = [
  "#3B82F6","#EF4444","#10B981","#F59E0B","#8B5CF6",
  "#EC4899","#06B6D4","#F97316","#84CC16","#6366F1",
];

function HoldingsPieChart({ holdings }: { holdings: Holding[] }) {
  const [hovered, setHovered] = useState<number | null>(null);

  const items = holdings
    .filter(h => (h.eval_amount ?? 0) > 0)
    .map((h, i) => ({ id: h.id, name: h.stock_name, value: h.eval_amount ?? 0, color: PIE_COLORS[i % PIE_COLORS.length] }));

  if (items.length === 0) return null;

  const total = items.reduce((s, it) => s + it.value, 0);
  const cx = 120, cy = 120, r = 100, innerR = 52;
  let cumAngle = -Math.PI / 2;

  const slices = items.map(it => {
    const angle = (it.value / total) * 2 * Math.PI;
    const start = cumAngle;
    cumAngle += angle;
    const end = cumAngle;
    const x1 = cx + r * Math.cos(start), y1 = cy + r * Math.sin(start);
    const x2 = cx + r * Math.cos(end),   y2 = cy + r * Math.sin(end);
    const ix1 = cx + innerR * Math.cos(start), iy1 = cy + innerR * Math.sin(start);
    const ix2 = cx + innerR * Math.cos(end),   iy2 = cy + innerR * Math.sin(end);
    const large = angle > Math.PI ? 1 : 0;
    const d = `M ${ix1} ${iy1} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} L ${ix2} ${iy2} A ${innerR} ${innerR} 0 ${large} 0 ${ix1} ${iy1} Z`;
    return { ...it, d, pct: (it.value / total * 100) };
  });

  const hov = hovered != null ? slices.find(s => s.id === hovered) : null;

  return (
    <div className="border rounded-lg p-4">
      <h2 className="text-sm font-semibold text-gray-600 mb-3">보유 비중</h2>
      <div className="flex flex-wrap items-center gap-6">
        <svg width={240} height={240} viewBox="0 0 240 240">
          {slices.map(s => (
            <path
              key={s.id}
              d={s.d}
              fill={s.color}
              opacity={hovered == null || hovered === s.id ? 1 : 0.4}
              stroke="white"
              strokeWidth={2}
              style={{ cursor: "pointer", transition: "opacity 0.15s" }}
              onMouseEnter={() => setHovered(s.id)}
              onMouseLeave={() => setHovered(null)}
            />
          ))}
          <text x={cx} y={cy - 8} textAnchor="middle" className="text-xs" fill="#6B7280" fontSize={11}>
            {hov ? hov.name : "전체"}
          </text>
          <text x={cx} y={cy + 10} textAnchor="middle" fill={hov ? hov.color : "#111827"} fontSize={16} fontWeight="bold">
            {hov ? `${hov.pct.toFixed(1)}%` : `${items.length}종목`}
          </text>
          <text x={cx} y={cy + 26} textAnchor="middle" fill="#9CA3AF" fontSize={10}>
            {hov ? `${hov.value.toLocaleString("ko-KR")}원` : `${total.toLocaleString("ko-KR")}원`}
          </text>
        </svg>
        <div className="flex flex-col gap-1.5 text-sm flex-1 min-w-40">
          {slices.map(s => (
            <div
              key={s.id}
              className={`flex items-center gap-2 cursor-pointer rounded px-1 py-0.5 transition-colors ${hovered === s.id ? "bg-gray-100" : ""}`}
              onMouseEnter={() => setHovered(s.id)}
              onMouseLeave={() => setHovered(null)}
            >
              <span className="w-3 h-3 rounded-full shrink-0" style={{ background: s.color }} />
              <span className="text-gray-700 flex-1 truncate">{s.name}</span>
              <span className="font-mono text-gray-500 text-xs">{s.pct.toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── 마크다운 인라인 파서 ──────────────────────────────────────────────────
function parseInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**"))
          return <strong key={i}>{part.slice(2, -2)}</strong>;
        if (part.startsWith("*") && part.endsWith("*"))
          return <em key={i}>{part.slice(1, -1)}</em>;
        return part;
      })}
    </>
  );
}

function AnalysisMarkdown({ text }: { text: string }) {
  const lines = text.split("\n");
  const nodes: React.ReactNode[] = [];
  let listBuffer: string[] = [];

  const flushList = () => {
    if (!listBuffer.length) return;
    nodes.push(
      <ul key={`ul-${nodes.length}`} className="space-y-1 my-1">
        {listBuffer.map((item, i) => {
          const isRisk = item.includes("🚨");
          return (
            <li key={i} className={`flex gap-2 text-sm leading-relaxed ${isRisk ? "text-red-700" : "text-gray-700"}`}>
              <span className="shrink-0 mt-1 w-1.5 h-1.5 rounded-full bg-gray-400 block" />
              <span>{parseInline(item)}</span>
            </li>
          );
        })}
      </ul>
    );
    listBuffer = [];
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { flushList(); continue; }

    // 최상단 헤더: **📊 ...보고서**
    if (line.startsWith("**📊")) {
      flushList();
      nodes.push(
        <h2 key={nodes.length} className="text-base font-bold text-gray-900 mb-3">
          {parseInline(line)}
        </h2>
      );
      continue;
    }

    // 섹션 헤더: - **N. ...**
    if (/^-\s*\*\*\d+\./.test(line)) {
      flushList();
      const inner = line.replace(/^-\s*/, "");
      nodes.push(
        <div key={nodes.length} className="mt-4 mb-1 text-sm font-semibold text-gray-800 border-b pb-1">
          {parseInline(inner)}
        </div>
      );
      continue;
    }

    // 일반 리스트 항목
    if (/^-\s+/.test(line)) {
      listBuffer.push(line.replace(/^-\s+/, ""));
      continue;
    }

    flushList();
    nodes.push(
      <p key={nodes.length} className="text-sm text-gray-700 leading-relaxed">
        {parseInline(line)}
      </p>
    );
  }
  flushList();
  return <div className="space-y-0.5">{nodes}</div>;
}

function PortfolioAnalysisPanel({
  analysis,
  isStale,
  loading,
  onRefresh,
}: {
  analysis: PortfolioAnalysis | null;
  isStale: boolean;
  loading: boolean;
  onRefresh: () => void;
}) {
  const [isOpen, setIsOpen] = useState(false);

  const dateLabel = analysis?.updated_at
    ? new Date(analysis.updated_at).toLocaleDateString("ko-KR", { month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <div className="border rounded-lg">
      {/* 헤더 — 항상 표시, 클릭으로 토글 */}
      <button
        type="button"
        onClick={() => setIsOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors rounded-lg"
      >
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-gray-600">AI 포트폴리오 분석</h2>
          {isStale && !loading && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">갱신 필요</span>
          )}
          {loading && (
            <span className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin inline-block" />
          )}
        </div>
        <div className="flex items-center gap-2">
          {dateLabel && (
            <span className="text-xs text-gray-400">{dateLabel} 기준</span>
          )}
          {isOpen
            ? <ChevronUp className="w-4 h-4 text-gray-400" />
            : <ChevronDown className="w-4 h-4 text-gray-400" />
          }
        </div>
      </button>

      {/* 펼침 내용 */}
      {isOpen && (
        <div className="px-4 pb-4 border-t">
          <div className="flex justify-end pt-3 mb-3">
            <button
              onClick={onRefresh}
              disabled={loading}
              className="flex items-center gap-1 text-xs px-2.5 py-1 rounded border hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <><span className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin inline-block" /> 분석 중…</>
              ) : (
                <>{analysis ? "새로 고침" : "분석 시작"}</>
              )}
            </button>
          </div>

          {loading && !analysis && (
            <div className="flex flex-col items-center justify-center py-10 gap-3 text-gray-400">
              <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin" />
              <span className="text-sm">AI가 포트폴리오를 분석하고 있습니다…</span>
            </div>
          )}

          {!loading && !analysis && (
            <div className="text-center py-8 text-gray-400 text-sm">
              <p>분석 결과가 없습니다.</p>
              <p className="text-xs mt-1">위 &quot;분석 시작&quot; 버튼을 눌러 AI 분석을 실행하세요.</p>
            </div>
          )}

          {analysis && (
            <div className={loading ? "opacity-50 pointer-events-none" : ""}>
              <AnalysisMarkdown text={analysis.analysis_text} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function pct(v: number | null | undefined) {
  if (v == null) return "N/A";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

function won(v: number | null | undefined) {
  if (v == null) return "N/A";
  return v.toLocaleString("ko-KR");
}

function ColorNum({ value, suffix = "" }: { value: number | null; suffix?: string }) {
  if (value == null) return <span className="text-gray-400">N/A</span>;
  const cls = value > 0 ? "text-red-500" : value < 0 ? "text-blue-500" : "text-gray-700";
  const sign = value > 0 ? "+" : "";
  return <span className={cls}>{sign}{value.toLocaleString("ko-KR")}{suffix}</span>;
}

function SummaryCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border rounded-lg p-4">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-lg font-semibold">{children}</div>
    </div>
  );
}

const GRADE_STYLE: Record<string, string> = {
  "관망":      "bg-green-100 text-green-700",
  "주의":      "bg-yellow-100 text-yellow-700",
  "매도 검토": "bg-orange-100 text-orange-700",
  "즉시 매도": "bg-red-100 text-red-700",
};

const GRADE_ICON: Record<string, { icon: string; hover: string }> = {
  "관망":      { icon: "text-green-400",  hover: "hover:bg-green-50" },
  "주의":      { icon: "text-yellow-500", hover: "hover:bg-yellow-50" },
  "매도 검토": { icon: "text-orange-500", hover: "hover:bg-orange-50" },
  "즉시 매도": { icon: "text-red-500",    hover: "hover:bg-red-50" },
};
const CATEGORY_STYLE: Record<string, string> = {
  "기술적":   "bg-blue-50 text-blue-700",
  "기본적":   "bg-purple-50 text-purple-700",
  "자산관리": "bg-orange-50 text-orange-700",
};

function SellAnalysisPanel({ analysis, avgPrice }: { analysis: SellAnalysis; avgPrice: number }) {
  const { sell_score, grade, signals, sell_levels, portfolio_weight, current_price } = analysis;
  const scoreColor =
    sell_score > 65 ? "bg-red-500" :
    sell_score > 40 ? "bg-orange-400" :
    sell_score > 20 ? "bg-yellow-400" : "bg-green-400";

  const gainPct = current_price != null
    ? ((current_price - avgPrice) / avgPrice * 100)
    : null;

  const levelRows = [
    { label: "손절가 −5%",   value: sell_levels.stop_loss_5,  note: "매수가 기준" },
    { label: "손절가 −10%",  value: sell_levels.stop_loss_10, note: "매수가 기준" },
    { label: "손절가 −15%",  value: sell_levels.stop_loss_15, note: "매수가 기준" },
    { label: "트레일링 기준가", value: sell_levels.trailing_high_ref, note: "최근 60일 고점" },
    { label: "트레일링 −7%", value: sell_levels.trailing_stop_7,  note: "고점 대비" },
    { label: "트레일링 −10%",value: sell_levels.trailing_stop_10, note: "고점 대비" },
    { label: "목표가 PER 15x", value: sell_levels.target_per15, note: "EPS 기반 보수적" },
    { label: "목표가 PER 20x", value: sell_levels.target_per20, note: "EPS 기반 중간" },
    { label: "목표가 PER 25x", value: sell_levels.target_per25, note: "EPS 기반 성장" },
    { label: "52주 최고가",  value: sell_levels.w52_high,       note: "연간 고점" },
  ].filter(r => r.value != null) as { label: string; value: number; note: string }[];

  return (
    <div className="bg-gray-50 border-t px-4 py-5 space-y-5">
      {/* 점수 */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex-1 min-w-48">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>매도 점수</span>
            <span className="font-semibold text-gray-700">{sell_score} / 100</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div className={`h-3 rounded-full transition-all ${scoreColor}`} style={{ width: `${sell_score}%` }} />
          </div>
        </div>
        <span className={`text-sm font-semibold px-3 py-1 rounded-full ${GRADE_STYLE[grade] ?? "bg-gray-100 text-gray-600"}`}>
          {grade}
        </span>
        {gainPct != null && (
          <span className={`text-sm font-mono ${gainPct >= 0 ? "text-red-500" : "text-blue-500"}`}>
            수익률 {gainPct >= 0 ? "+" : ""}{gainPct.toFixed(2)}%
          </span>
        )}
        {portfolio_weight != null && (
          <span className="text-sm text-gray-500">비중 {portfolio_weight.toFixed(1)}%</span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* 매도 신호 목록 */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">활성 매도 신호</h3>
          {signals.length === 0 ? (
            <p className="text-sm text-gray-400">감지된 매도 신호가 없습니다.</p>
          ) : (
            <div className="space-y-2">
              {signals.map((s, i) => (
                <div key={i} className="flex gap-2 items-start text-sm">
                  <span className={`shrink-0 text-xs px-1.5 py-0.5 rounded font-medium mt-0.5 ${CATEGORY_STYLE[s.category] ?? "bg-gray-100 text-gray-600"}`}>
                    {s.category}
                  </span>
                  <div className="flex-1">
                    <div className="font-medium text-gray-800">{s.name}
                      <span className="ml-1 text-xs text-gray-400">(+{s.pts}점)</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">{s.description}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 매도 가격대 */}
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">매도 가격대</h3>
          <div className="space-y-1 text-sm">
            {levelRows.map(({ label, value, note }) => {
              const isCurrent = current_price != null && Math.abs(value - current_price) / current_price < 0.02;
              const isBelow   = current_price != null && current_price < value;
              return (
                <div key={label} className={`flex justify-between items-center py-1 border-b last:border-0 ${isCurrent ? "bg-yellow-50 -mx-1 px-1 rounded" : ""}`}>
                  <div>
                    <span className="text-gray-600">{label}</span>
                    <span className="text-xs text-gray-400 ml-1">({note})</span>
                    {isCurrent && <span className="ml-1 text-xs text-yellow-600 font-medium">◀ 현재 근접</span>}
                  </div>
                  <span className={`font-mono font-medium ${isBelow ? "text-blue-500" : "text-gray-800"}`}>
                    {value.toLocaleString("ko-KR")}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

const EMPTY_FORM = { stock_code: "", stock_name: "", avg_price: "", quantity: "", memo: "" };

export default function PortfolioPage() {
  const { profiles, selectedId, setSelectedId, createProfile, updateProfile, deleteProfile } = useProfile();

  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [summary, setSummary] = useState<HoldingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // add form
  const [form, setForm] = useState(EMPTY_FORM);
  const [adding, setAdding] = useState(false);
  const [showForm, setShowForm] = useState(false);

  // inline edit
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ avg_price: "", quantity: "", memo: "", profile_id: null as number | null });
  const [saving, setSaving] = useState(false);

  // portfolio AI analysis
  const [portfolioAnalysis, setPortfolioAnalysis] = useState<PortfolioAnalysis | null>(null);
  const [analysisStale, setAnalysisStale] = useState(true);
  const [analysisLoading2, setAnalysisLoading2] = useState(false);

  const [priceUpdatedAt, setPriceUpdatedAt] = useState<string | null>(null);

  // sell analysis
  const [analysisId, setAnalysisId] = useState<number | null>(null);
  const [analysisData, setAnalysisData] = useState<Record<number, SellAnalysis>>({});
  const [analysisLoading, setAnalysisLoading] = useState<number | null>(null);

  // new profile form
  const [showNewProfile, setShowNewProfile] = useState(false);
  const [newProfileName, setNewProfileName] = useState("");
  const [newProfileType, setNewProfileType] = useState<"quant" | "dividend">("quant");
  const [creatingProfile, setCreatingProfile] = useState(false);

  // edit profile form
  const [editProfileId, setEditProfileId] = useState<number | null>(null);
  const [editProfileName, setEditProfileName] = useState("");
  const [editProfileType, setEditProfileType] = useState<"quant" | "dividend">("quant");
  const [savingProfile, setSavingProfile] = useState(false);

  const loadPortfolioAnalysis = useCallback(async (holdings: Holding[], autoRefresh = false) => {
    const hash = [...holdings]
      .sort((a, b) => a.stock_code.localeCompare(b.stock_code))
      .map(h => `${h.stock_code}:${h.quantity}:${h.avg_price}`)
      .join("|");
    const hashKey = btoa(unescape(encodeURIComponent(hash))).slice(0, 16);

    try {
      const res = await api.getPortfolioAnalysis(selectedId, hashKey);
      if (res.data) setPortfolioAnalysis(res.data);
      setAnalysisStale(res.is_stale);

      if (res.is_stale && autoRefresh) {
        setAnalysisLoading2(true);
        try {
          const r2 = await api.requestPortfolioAnalysis(selectedId);
          setPortfolioAnalysis(r2.data);
          setAnalysisStale(false);
        } catch { /* silent */ } finally {
          setAnalysisLoading2(false);
        }
      }
    } catch { /* silent */ }
  }, [selectedId]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setAnalysisData({});
    setPortfolioAnalysis(null);
    setAnalysisStale(true);
    try {
      const res = await api.getHoldings(selectedId);
      setHoldings(res.data);
      setSummary(res.summary);
      setPriceUpdatedAt(res.price_fetched_at ?? null);
      // 매도 분석 백그라운드 일괄 조회 (UI 블로킹 없음)
      res.data.forEach(h => {
        api.getSellAnalysis(h.id)
          .then(r => setAnalysisData(prev => ({ ...prev, [h.id]: r.data })))
          .catch(() => {});
      });
      // 포트폴리오 AI 분석 자동 체크 (변경/만료 시 자동 갱신)
      if (res.data.length > 0) {
        loadPortfolioAnalysis(res.data, true);
      }
    } catch {
      setError("데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [selectedId, loadPortfolioAnalysis]);

  useEffect(() => { load(); }, [load]);

  async function handleRefreshAnalysis() {
    if (analysisLoading2) return;
    setAnalysisLoading2(true);
    try {
      const r = await api.requestPortfolioAnalysis(selectedId);
      setPortfolioAnalysis(r.data);
      setAnalysisStale(false);
    } catch (e: unknown) {
      alert((e as Error).message);
    } finally {
      setAnalysisLoading2(false);
    }
  }

  async function handleCreateProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!newProfileName.trim()) return;
    setCreatingProfile(true);
    try {
      const profile = await createProfile(newProfileName.trim(), newProfileType);
      setSelectedId(profile.id);
      setNewProfileName("");
      setNewProfileType("quant");
      setShowNewProfile(false);
    } catch (e: unknown) {
      alert((e as Error).message);
    } finally {
      setCreatingProfile(false);
    }
  }

  function startEditProfile(p: { id: number; name: string; analysis_type: "quant" | "dividend" }) {
    setEditProfileId(p.id);
    setEditProfileName(p.name);
    setEditProfileType(p.analysis_type ?? "quant");
  }

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!editProfileName.trim() || editProfileId == null) return;
    setSavingProfile(true);
    try {
      await updateProfile(editProfileId, { name: editProfileName.trim(), analysis_type: editProfileType });
      setEditProfileId(null);
    } catch (e: unknown) {
      alert((e as Error).message);
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleDeleteProfile(id: number, name: string) {
    if (!confirm(`"${name}" 프로필을 삭제하시겠습니까?\n해당 프로필의 보유 종목은 미분류로 이동됩니다.`)) return;
    await deleteProfile(id);
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const avgPrice = parseInt(form.avg_price.replace(/,/g, ""));
    const qty = parseInt(form.quantity.replace(/,/g, ""));
    if (!form.stock_code || !form.stock_name || isNaN(avgPrice) || isNaN(qty)) return;
    setAdding(true);
    try {
      await api.addHolding({
        stock_code: form.stock_code.trim(),
        stock_name: form.stock_name.trim(),
        avg_price: avgPrice,
        quantity: qty,
        memo: form.memo || undefined,
        profile_id: selectedId ?? undefined,
      });
      setForm(EMPTY_FORM);
      setShowForm(false);
      await load();
    } catch (e: unknown) {
      alert((e as Error).message);
    } finally {
      setAdding(false);
    }
  }

  function startEdit(h: Holding) {
    setEditId(h.id);
    setEditForm({
      avg_price: h.avg_price.toString(),
      quantity: h.quantity.toString(),
      memo: h.memo ?? "",
      profile_id: h.profile_id ?? null,
    });
  }

  async function handleSave(id: number) {
    setSaving(true);
    try {
      await api.updateHolding(id, {
        avg_price: parseInt(editForm.avg_price.replace(/,/g, "")),
        quantity: parseInt(editForm.quantity.replace(/,/g, "")),
        memo: editForm.memo || undefined,
        profile_id: editForm.profile_id,
      });
      setEditId(null);
      await load();
    } catch (e: unknown) {
      alert((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function toggleAnalysis(id: number) {
    if (analysisId === id) { setAnalysisId(null); return; }
    setAnalysisId(id);
    if (analysisData[id]) return; // already fetched
    setAnalysisLoading(id);
    try {
      const res = await api.getSellAnalysis(id);
      setAnalysisData(prev => ({ ...prev, [id]: res.data }));
    } catch (e: unknown) {
      alert((e as Error).message);
      setAnalysisId(null);
    } finally {
      setAnalysisLoading(null);
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`"${name}" 보유 종목을 삭제하시겠습니까?`)) return;
    try {
      await api.deleteHolding(id);
      await load();
    } catch (e: unknown) {
      alert((e as Error).message);
    }
  }

  const totalChangeToday = holdings.reduce((acc, h) => {
    if (h.current_price == null || h.change_rate == null) return acc;
    const prevPrice = h.current_price / (1 + h.change_rate / 100);
    return acc + (h.current_price - prevPrice) * h.quantity;
  }, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">보유 종목</h1>
        <button
          onClick={() => setShowForm(v => !v)}
          className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" /> 종목 추가
        </button>
      </div>

      {/* 프로필 선택기 */}
      <div className="flex flex-wrap items-center gap-2">
        {/* 전체 버튼 */}
        <button
          onClick={() => setSelectedId(null)}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            selectedId == null ? "bg-gray-800 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          전체
        </button>

        {/* 프로필 목록 */}
        {profiles.map(p => {
          const isSelected = selectedId === p.id;
          const isEditing = editProfileId === p.id;
          const typeLabel = p.analysis_type === "dividend"
            ? <span className="ml-1 text-xs opacity-70">배당</span>
            : <span className="ml-1 text-xs opacity-70">퀀트</span>;

          if (isEditing) {
            return (
              <form key={p.id} onSubmit={handleSaveProfile} className="flex items-center gap-1 flex-wrap">
                <input
                  autoFocus
                  value={editProfileName}
                  onChange={e => setEditProfileName(e.target.value)}
                  className="border rounded-full px-3 py-1 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-300"
                />
                {/* 타입 토글 */}
                <div className="flex rounded-full border overflow-hidden text-xs">
                  <button
                    type="button"
                    onClick={() => setEditProfileType("quant")}
                    className={`px-2.5 py-1 transition-colors ${editProfileType === "quant" ? "bg-indigo-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
                  >
                    퀀트
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditProfileType("dividend")}
                    className={`px-2.5 py-1 transition-colors ${editProfileType === "dividend" ? "bg-emerald-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
                  >
                    배당
                  </button>
                </div>
                <button
                  type="submit"
                  disabled={savingProfile}
                  className="px-2 py-1 text-xs bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50"
                >
                  {savingProfile ? "…" : "저장"}
                </button>
                <button
                  type="button"
                  onClick={() => setEditProfileId(null)}
                  className="px-2 py-1 text-xs border rounded-full hover:bg-gray-100"
                >
                  취소
                </button>
              </form>
            );
          }

          return (
            <div key={p.id} className="relative group flex items-center gap-0.5">
              <button
                onClick={() => setSelectedId(isSelected ? null : p.id)}
                className={`pl-3 pr-2 py-1.5 rounded-full text-sm font-medium transition-colors flex items-center ${
                  isSelected
                    ? p.analysis_type === "dividend" ? "bg-emerald-600 text-white" : "bg-blue-600 text-white"
                    : p.analysis_type === "dividend" ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100" : "bg-blue-50 text-blue-700 hover:bg-blue-100"
                }`}
              >
                {p.name}{typeLabel}
              </button>
              {/* 편집/삭제 버튼 — hover 시 표시 */}
              <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-0.5">
                <button
                  onClick={() => startEditProfile(p)}
                  className="w-5 h-5 flex items-center justify-center rounded-full bg-gray-200 text-gray-500 hover:bg-gray-300 text-xs"
                  title="프로필 편집"
                >
                  ✎
                </button>
                <button
                  onClick={() => handleDeleteProfile(p.id, p.name)}
                  className="w-5 h-5 flex items-center justify-center rounded-full bg-gray-200 text-gray-500 hover:bg-red-200 hover:text-red-600 text-xs"
                  title="프로필 삭제"
                >
                  ×
                </button>
              </div>
            </div>
          );
        })}

        {/* 새 프로필 추가 */}
        {showNewProfile ? (
          <form onSubmit={handleCreateProfile} className="flex items-center gap-1 flex-wrap">
            <input
              autoFocus
              value={newProfileName}
              onChange={e => setNewProfileName(e.target.value)}
              placeholder="프로필 이름"
              className="border rounded-full px-3 py-1 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
            {/* 타입 토글 */}
            <div className="flex rounded-full border overflow-hidden text-xs">
              <button
                type="button"
                onClick={() => setNewProfileType("quant")}
                className={`px-2.5 py-1 transition-colors ${newProfileType === "quant" ? "bg-indigo-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
              >
                퀀트
              </button>
              <button
                type="button"
                onClick={() => setNewProfileType("dividend")}
                className={`px-2.5 py-1 transition-colors ${newProfileType === "dividend" ? "bg-emerald-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
              >
                배당
              </button>
            </div>
            <button
              type="submit"
              disabled={creatingProfile}
              className="px-2 py-1 text-xs bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50"
            >
              {creatingProfile ? "…" : "추가"}
            </button>
            <button
              type="button"
              onClick={() => { setShowNewProfile(false); setNewProfileName(""); setNewProfileType("quant"); }}
              className="px-2 py-1 text-xs border rounded-full hover:bg-gray-100"
            >
              취소
            </button>
          </form>
        ) : (
          <button
            onClick={() => setShowNewProfile(true)}
            className="w-7 h-7 flex items-center justify-center rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 text-lg leading-none"
            title="프로필 추가"
          >
            +
          </button>
        )}
      </div>

      {/* 요약 카드 */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryCard label="총 매입금액">
            <span className="font-mono">{won(summary.total_purchase)}</span>
          </SummaryCard>
          <SummaryCard label="총 평가금액">
            <span className="font-mono">{won(summary.total_eval)}</span>
          </SummaryCard>
          <SummaryCard label="총 평가손익">
            <ColorNum value={summary.total_profit_loss} />
          </SummaryCard>
          <SummaryCard label="총 수익률">
            <span className={
              summary.total_profit_rate == null ? "text-gray-400"
                : summary.total_profit_rate > 0 ? "text-red-500"
                : summary.total_profit_rate < 0 ? "text-blue-500"
                : "text-gray-700"
            }>
              {pct(summary.total_profit_rate)}
            </span>
          </SummaryCard>
        </div>
      )}

      {/* 보유 비중 파이 차트 */}
      {holdings.length > 0 && <HoldingsPieChart holdings={holdings} />}

      {/* AI 포트폴리오 분석 */}
      {holdings.length > 0 && (
        <PortfolioAnalysisPanel
          analysis={portfolioAnalysis}
          isStale={analysisStale}
          loading={analysisLoading2}
          onRefresh={handleRefreshAnalysis}
        />
      )}

      {/* 오늘 평가손익 */}
      {holdings.length > 0 && (
        <div className="text-sm text-gray-500">
          오늘 손익{" "}
          <span className={totalChangeToday > 0 ? "text-red-500 font-semibold" : totalChangeToday < 0 ? "text-blue-500 font-semibold" : "text-gray-700"}>
            {totalChangeToday > 0 ? "+" : ""}{Math.round(totalChangeToday).toLocaleString("ko-KR")}원
          </span>
        </div>
      )}

      {/* 종목 추가 폼 */}
      {showForm && (
        <form onSubmit={handleAdd} className="border rounded-lg p-4 bg-gray-50 space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">종목 코드</label>
              <input
                value={form.stock_code}
                onChange={e => setForm(f => ({ ...f, stock_code: e.target.value }))}
                placeholder="005930"
                className="w-full border rounded px-2 py-1.5 text-sm"
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">종목명</label>
              <input
                value={form.stock_name}
                onChange={e => setForm(f => ({ ...f, stock_name: e.target.value }))}
                placeholder="삼성전자"
                className="w-full border rounded px-2 py-1.5 text-sm"
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">평균 단가 (원)</label>
              <input
                value={form.avg_price}
                onChange={e => setForm(f => ({ ...f, avg_price: e.target.value }))}
                placeholder="70000"
                type="number"
                min="1"
                className="w-full border rounded px-2 py-1.5 text-sm"
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">수량 (주)</label>
              <input
                value={form.quantity}
                onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
                placeholder="10"
                type="number"
                min="1"
                className="w-full border rounded px-2 py-1.5 text-sm"
                required
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">메모 (선택)</label>
            <input
              value={form.memo}
              onChange={e => setForm(f => ({ ...f, memo: e.target.value }))}
              placeholder="장기 보유 등"
              className="w-full border rounded px-2 py-1.5 text-sm"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => { setShowForm(false); setForm(EMPTY_FORM); }}
              className="px-3 py-1.5 text-sm border rounded hover:bg-gray-100"
            >취소</button>
            <button
              type="submit"
              disabled={adding}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >{adding ? "추가 중…" : "추가"}</button>
          </div>
        </form>
      )}

      {/* 보유 종목 테이블 */}
      {loading ? (
        <div className="text-center py-20 text-gray-400">불러오는 중…</div>
      ) : error ? (
        <div className="text-center py-10 text-red-400">{error}</div>
      ) : holdings.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p>보유 종목이 없습니다.</p>
          <p className="text-sm mt-1">위 &quot;종목 추가&quot; 버튼으로 등록하세요.</p>
        </div>
      ) : (
        <div className="border rounded-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-3 py-3 text-left">종목</th>
                <th className="px-3 py-3 text-right">
                  <div>현재가</div>
                  {priceUpdatedAt && (
                    <div className="text-gray-400 font-normal normal-case mt-0.5">
                      {new Date(priceUpdatedAt).toLocaleString("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })} 기준
                    </div>
                  )}
                </th>
                <th className="px-3 py-3 text-right">등락률</th>
                <th className="px-3 py-3 text-right">평균단가</th>
                <th className="px-3 py-3 text-right">수량</th>
                <th className="px-3 py-3 text-right">매입금액</th>
                <th className="px-3 py-3 text-right">평가금액</th>
                <th className="px-3 py-3 text-right">평가손익</th>
                <th className="px-3 py-3 text-right">수익률</th>
                <th className="px-3 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {holdings.map(h => (<>
                <tr key={h.id} className="hover:bg-gray-50">
                  {/* 종목명 */}
                  <td className="px-3 py-3">
                    <Link href={`/stocks/${h.stock_code}?from=portfolio`} className="hover:underline">
                      <div className="font-medium">{h.stock_name}</div>
                      <div className="flex items-center gap-1.5 text-xs text-gray-400">
                        <span>{h.stock_code}</span>
                        {h.market && (
                          <span className={`px-1.5 py-0.5 rounded font-semibold ${
                            h.market === "KOSPI"
                              ? "bg-blue-50 text-blue-600"
                              : "bg-emerald-50 text-emerald-600"
                          }`}>
                            {h.market}
                          </span>
                        )}
                      </div>
                    </Link>
                    <div className="flex flex-wrap items-center gap-1 mt-0.5">
                      {h.stock_type && (
                        <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                          h.stock_type === "ETF"  ? "bg-purple-50 text-purple-700" :
                          h.stock_type === "ETN"  ? "bg-orange-50 text-orange-700" :
                          h.stock_type === "리츠" ? "bg-emerald-50 text-emerald-700" :
                          "bg-gray-100 text-gray-500"
                        }`}>
                          {h.stock_type}
                        </span>
                      )}
                      {h.sector_name && (
                        <span className="text-xs text-gray-400">{h.sector_name}</span>
                      )}
                    </div>
                    {h.memo && <div className="text-xs text-gray-400 mt-0.5">{h.memo}</div>}
                    {h.profile_id != null && (
                      <div className="mt-0.5">
                        <span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-600">
                          {profiles.find(p => p.id === h.profile_id)?.name ?? "프로필"}
                        </span>
                      </div>
                    )}
                  </td>

                  {/* 현재가 */}
                  <td className="px-3 py-3 text-right font-mono">
                    {h.current_price != null ? h.current_price.toLocaleString("ko-KR") : <span className="text-gray-400">N/A</span>}
                  </td>

                  {/* 등락률 */}
                  <td className={`px-3 py-3 text-right font-mono font-semibold ${h.change_rate == null ? "" : h.change_rate >= 0 ? "text-red-500" : "text-blue-500"}`}>
                    {h.change_rate != null ? pct(h.change_rate) : <span className="text-gray-400">N/A</span>}
                  </td>

                  {/* 편집 가능 필드 */}
                  {editId === h.id ? (
                    <>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          value={editForm.avg_price}
                          onChange={e => setEditForm(f => ({ ...f, avg_price: e.target.value }))}
                          className="w-24 border rounded px-1.5 py-1 text-sm text-right"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          value={editForm.quantity}
                          onChange={e => setEditForm(f => ({ ...f, quantity: e.target.value }))}
                          className="w-16 border rounded px-1.5 py-1 text-sm text-right"
                        />
                      </td>
                      <td colSpan={2} className="px-3 py-2">
                        <input
                          value={editForm.memo}
                          onChange={e => setEditForm(f => ({ ...f, memo: e.target.value }))}
                          placeholder="메모"
                          className="w-full border rounded px-1.5 py-1 text-sm"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <select
                          value={editForm.profile_id ?? ""}
                          onChange={e => setEditForm(f => ({ ...f, profile_id: e.target.value ? parseInt(e.target.value) : null }))}
                          className="w-full border rounded px-1.5 py-1 text-sm bg-white"
                        >
                          <option value="">미분류</option>
                          {profiles.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-3 py-2">—</td>
                    </>
                  ) : (
                    <>
                      <td className="px-3 py-3 text-right font-mono">{won(h.avg_price)}</td>
                      <td className="px-3 py-3 text-right font-mono">{h.quantity.toLocaleString("ko-KR")}</td>
                      <td className="px-3 py-3 text-right font-mono text-gray-600">{won(h.purchase_amount)}</td>
                      <td className="px-3 py-3 text-right font-mono">{won(h.eval_amount)}</td>
                      <td className="px-3 py-3 text-right font-mono">
                        <ColorNum value={h.profit_loss} />
                      </td>
                      <td className={`px-3 py-3 text-right font-mono font-semibold ${h.profit_rate == null ? "" : h.profit_rate > 0 ? "text-red-500" : h.profit_rate < 0 ? "text-blue-500" : "text-gray-700"}`}>
                        {pct(h.profit_rate)}
                      </td>
                    </>
                  )}

                  {/* 액션 */}
                  <td className="px-3 py-3">
                    <div className="flex gap-1 justify-end">
                      {editId === h.id ? (
                        <>
                          <button onClick={() => handleSave(h.id)} disabled={saving}
                            className="p-1 text-green-600 hover:bg-green-50 rounded" title="저장">
                            <Check className="w-4 h-4" />
                          </button>
                          <button onClick={() => setEditId(null)}
                            className="p-1 text-gray-400 hover:bg-gray-100 rounded" title="취소">
                            <X className="w-4 h-4" />
                          </button>
                        </>
                      ) : (
                        <>
                          {(() => {
                            const grade = analysisData[h.id]?.grade;
                            const gi = grade ? GRADE_ICON[grade] : null;
                            const isOpen = analysisId === h.id;
                            const isLoading = analysisLoading === h.id;
                            return (
                              <button
                                onClick={() => toggleAnalysis(h.id)}
                                className={`p-1 rounded ${isOpen ? `${gi?.icon ?? "text-gray-400"} bg-white ring-1 ring-current` : `${gi?.icon ?? "text-gray-300"} ${gi?.hover ?? "hover:bg-gray-50"}`}`}
                                title={grade ? `매도 분석 (${grade})` : "매도 분석 로딩 중…"}
                              >
                                {isLoading
                                  ? <span className="w-4 h-4 block animate-spin border-2 border-current border-t-transparent rounded-full" />
                                  : isOpen ? <ChevronUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                              </button>
                            );
                          })()}
                          <button onClick={() => startEdit(h)}
                            className="p-1 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded" title="편집">
                            <Pencil className="w-4 h-4" />
                          </button>
                          <button onClick={() => handleDelete(h.id, h.stock_name)}
                            className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded" title="삭제">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
                {/* 매도 분석 패널 */}
                {analysisId === h.id && analysisData[h.id] && (
                  <tr key={`analysis-${h.id}`}>
                    <td colSpan={10} className="p-0">
                      <SellAnalysisPanel analysis={analysisData[h.id]} avgPrice={h.avg_price} />
                    </td>
                  </tr>
                )}
              </>))}
            </tbody>

            {/* 합계 행 */}
            {summary && (
              <tfoot className="bg-gray-50 font-semibold text-sm border-t-2">
                <tr>
                  <td className="px-3 py-3 text-gray-600" colSpan={5}>합계</td>
                  <td className="px-3 py-3 text-right font-mono">{won(summary.total_purchase)}</td>
                  <td className="px-3 py-3 text-right font-mono">{won(summary.total_eval)}</td>
                  <td className="px-3 py-3 text-right font-mono">
                    <ColorNum value={summary.total_profit_loss} />
                  </td>
                  <td className={`px-3 py-3 text-right font-mono ${summary.total_profit_rate == null ? "" : summary.total_profit_rate > 0 ? "text-red-500" : "text-blue-500"}`}>
                    {pct(summary.total_profit_rate)}
                  </td>
                  <td />
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}
    </div>
  );
}
