"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { StockDetail, ExpectedReturn, StrategyAnalysisData } from "@/lib/types";
import { useFavorites } from "@/hooks/useFavorites";
import { Star } from "lucide-react";
import Link from "next/link";

function fmt(v: number | null | undefined, digits = 0): string {
  if (v == null) return "N/A";
  return v.toLocaleString("ko-KR", { maximumFractionDigits: digits });
}

function RsiBar({ value }: { value: number | null }) {
  if (value == null) return <span className="text-gray-400">N/A</span>;
  const color = value < 30 ? "text-blue-500" : value > 70 ? "text-red-500" : "text-green-600";
  const label = value < 30 ? "과매도" : value > 70 ? "과매수" : "정상";
  return (
    <span className={`font-mono font-semibold ${color}`}>
      {value.toFixed(1)} <span className="text-xs font-normal">({label})</span>
    </span>
  );
}

function MfiLabel({ value }: { value: number | null }) {
  if (value == null) return <span className="text-gray-400">N/A</span>;
  const color = value < 20 ? "text-blue-500" : value > 80 ? "text-red-500" : "text-gray-700";
  const label = value < 20 ? "과매도" : value > 80 ? "과매수" : "";
  return (
    <span className={`font-mono font-semibold ${color}`}>
      {value.toFixed(1)}{label && <span className="text-xs font-normal ml-1">({label})</span>}
    </span>
  );
}

function CciLabel({ value }: { value: number | null }) {
  if (value == null) return <span className="text-gray-400">N/A</span>;
  const color = value < -100 ? "text-blue-500" : value > 100 ? "text-red-500" : "text-gray-700";
  const label = value < -100 ? "과매도" : value > 100 ? "과매수" : "";
  return (
    <span className={`font-mono font-semibold ${color}`}>
      {value.toFixed(0)}{label && <span className="text-xs font-normal ml-1">({label})</span>}
    </span>
  );
}

function AdxLabel({ adx, plusDi, minusDi }: { adx: number | null; plusDi: number | null; minusDi: number | null }) {
  if (adx == null) return <span className="text-gray-400">N/A</span>;
  const strong = adx >= 20;
  const color = strong ? (plusDi != null && minusDi != null && plusDi > minusDi ? "text-red-500" : "text-blue-500") : "text-gray-700";
  return (
    <span className={`font-mono font-semibold ${color}`}>
      {adx.toFixed(1)}{strong && <span className="text-xs font-normal ml-1">(강한 추세)</span>}
    </span>
  );
}

function CloudBadge({ position }: { position: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    above_cloud: { label: "구름 위 (강세)", cls: "bg-red-50 text-red-600" },
    in_cloud:    { label: "구름 안 (중립)", cls: "bg-yellow-50 text-yellow-700" },
    below_cloud: { label: "구름 아래 (약세)", cls: "bg-blue-50 text-blue-600" },
    unknown:     { label: "데이터 부족", cls: "bg-gray-100 text-gray-500" },
  };
  const { label, cls } = map[position] ?? map.unknown;
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>{label}</span>;
}

function CategoryBar({ label, score, max = 10, color }: { label: string; score: number; max?: number; color: string }) {
  const pct = Math.min(100, (score / max) * 100);
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-500">{label}</span>
        <span className="font-semibold">{score}<span className="text-gray-400 font-normal">/{max}</span></span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-1.5">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ExpectedReturnSection({ er }: { er: ExpectedReturn }) {
  const isApproved = er.verdict === "진입 승인";
  const verdictCls = isApproved
    ? "bg-green-100 text-green-700 border-green-200"
    : "bg-orange-50 text-orange-700 border-orange-200";

  return (
    <div className="border rounded-lg p-5 space-y-4">
      <h2 className="font-semibold">기대 수익률 분석</h2>

      {/* 목표가 / 손절가 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        {[
          { label: "현재가", value: `${er.current_price.toLocaleString("ko-KR")}원`, color: "" },
          {
            label: `펀더멘탈 목표가`,
            value: er.target_price ? `${er.target_price.toLocaleString("ko-KR")}원` : "N/A",
            sub: er.target_upside != null ? `+${er.target_upside.toFixed(1)}%` : undefined,
            color: "text-red-600",
          },
          {
            label: "손절 기준가",
            value: `${er.stop_loss.toLocaleString("ko-KR")}원`,
            sub: `${er.stop_loss_rate.toFixed(1)}%`,
            color: "text-blue-600",
          },
          {
            label: `손익비`,
            value: er.risk_reward != null ? `${er.risk_reward.toFixed(1)} : 1` : "N/A",
            color: er.risk_reward != null && er.risk_reward >= 2 ? "text-green-600" : "text-orange-500",
          },
        ].map(({ label, value, sub, color }) => (
          <div key={label} className="border rounded-lg p-3">
            <div className="text-xs text-gray-500 mb-1">{label}</div>
            <div className={`font-mono font-semibold ${color}`}>{value}</div>
            {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
          </div>
        ))}
      </div>

      {/* 목표가 산출 근거 */}
      {(er.target_price_per || er.target_price_pbr) && (
        <div className="text-xs text-gray-500 flex flex-wrap gap-4">
          {er.target_price_per && (
            <span>
              Target PER({er.sector_per}×
              {er.sector_name
                ? <span className="text-gray-400"> · {er.sector_name} 섹터 평균</span>
                : <span className="text-gray-400"> · 기본값</span>
              }
              ): <span className="font-mono text-gray-700">{er.target_price_per.toLocaleString("ko-KR")}원</span>
            </span>
          )}
          {er.target_price_pbr && (
            <span>PBR-ROE(COE {er.coe}%): <span className="font-mono text-gray-700">{er.target_price_pbr.toLocaleString("ko-KR")}원</span></span>
          )}
        </div>
      )}

      {/* 확률 기댓값 */}
      {er.expected_value != null && (
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-500">확률 기반 기댓값</span>
          <span className={`font-mono font-semibold ${er.expected_value >= 0 ? "text-red-500" : "text-blue-500"}`}>
            {er.expected_value >= 0 ? "+" : ""}{er.expected_value.toFixed(1)}%
          </span>
          <span className="text-xs text-gray-400">(상승 60% / 하락 40% 반영)</span>
        </div>
      )}

      {/* 진입 판단 */}
      {er.verdict && (
        <div className={`border rounded-lg px-4 py-3 text-sm ${verdictCls}`}>
          <span className="font-bold mr-2">{er.verdict}</span>
          <span className="text-xs">{er.verdict_reason}</span>
        </div>
      )}
    </div>
  );
}

function QuantResultView({ data }: { data: StrategyAnalysisData }) {
  const score = data.quant_score ?? 0;
  const scoreColor = score >= 70 ? "bg-green-500" : score >= 55 ? "bg-yellow-400" : score >= 40 ? "bg-orange-400" : "bg-blue-400";
  const verdictIsApproved = data.verdict === "진입 승인";
  const verdictCls = verdictIsApproved ? "bg-green-100 text-green-700 border-green-200" : "bg-orange-50 text-orange-700 border-orange-200";
  const fs = data.factor_scores;

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-gray-600">퀀트 점수</span>
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold font-mono">{score}<span className="text-sm font-normal text-gray-400">/100</span></span>
            {data.direction_hint && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700">{data.direction_hint}</span>
            )}
          </div>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-2">
          <div className={`h-2 rounded-full ${scoreColor}`} style={{ width: `${score}%` }} />
        </div>
      </div>

      {fs && (
        <div className="grid grid-cols-3 gap-3 text-sm">
          <div className="border rounded-lg p-3 space-y-1.5">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-indigo-600">모멘텀</span>
              <span className="font-mono font-bold">{fs.momentum.score}<span className="text-gray-400 font-normal">/{fs.momentum.max}</span></span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-1">
              <div className="h-1 rounded-full bg-indigo-400" style={{ width: `${(fs.momentum.score / fs.momentum.max) * 100}%` }} />
            </div>
            <div className="text-xs text-gray-500 space-y-0.5">
              <div className="flex justify-between">
                <span>MA20 이격도</span>
                <span className="font-mono">{fs.momentum.ma20_deviation != null ? `${((fs.momentum.ma20_deviation - 1) * 100).toFixed(1)}%` : "N/A"}</span>
              </div>
              <div className="flex justify-between">
                <span>RSI14</span>
                <span className="font-mono">{fs.momentum.rsi14 != null ? fs.momentum.rsi14.toFixed(1) : "N/A"}</span>
              </div>
            </div>
          </div>

          <div className="border rounded-lg p-3 space-y-1.5">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-green-600">가치</span>
              <span className="font-mono font-bold">{fs.value.score}<span className="text-gray-400 font-normal">/{fs.value.max}</span></span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-1">
              <div className="h-1 rounded-full bg-green-400" style={{ width: `${(fs.value.score / fs.value.max) * 100}%` }} />
            </div>
            <div className="text-xs text-gray-500 space-y-0.5">
              <div className="flex justify-between">
                <span>PER</span>
                <span className="font-mono">{(fs.value.per != null && fs.value.per > 0) ? `${fs.value.per.toFixed(1)}배` : "N/A"}</span>
              </div>
              <div className="flex justify-between">
                <span>PBR</span>
                <span className="font-mono">{fs.value.pbr != null ? `${fs.value.pbr.toFixed(2)}배` : "N/A"}</span>
              </div>
            </div>
          </div>

          <div className="border rounded-lg p-3 space-y-1.5">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-yellow-600">변동성</span>
              <span className="font-mono font-bold">{fs.volatility.score}<span className="text-gray-400 font-normal">/{fs.volatility.max}</span></span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-1">
              <div className="h-1 rounded-full bg-yellow-400" style={{ width: `${(fs.volatility.score / fs.volatility.max) * 100}%` }} />
            </div>
            <div className="text-xs text-gray-500">
              <div className="flex justify-between">
                <span>연환산변동성</span>
                <span className="font-mono">{fs.volatility.annualized_vol != null ? `${fs.volatility.annualized_vol.toFixed(1)}%` : "N/A"}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className={`border rounded-lg px-4 py-3 text-sm ${verdictCls}`}>
        <span className="font-bold mr-2">{data.verdict}</span>
        <span className="text-xs">{data.verdict_reason}</span>
      </div>
    </div>
  );
}

function DividendResultView({ data }: { data: StrategyAnalysisData }) {
  const verdictIsApproved = data.verdict === "진입 승인";
  const verdictCls = data.verdict === "판단 불가"
    ? "bg-gray-100 text-gray-600 border-gray-200"
    : verdictIsApproved ? "bg-green-100 text-green-700 border-green-200"
    : "bg-orange-50 text-orange-700 border-orange-200";
  const score = data.stability_score ?? 0;
  const scoreBarColor = score >= 70 ? "bg-green-500" : score >= 40 ? "bg-yellow-400" : "bg-red-400";
  const gradeColor = data.stability_grade === "안정"
    ? "text-green-600 bg-green-50 border-green-200"
    : data.stability_grade === "모니터링"
    ? "text-yellow-700 bg-yellow-50 border-yellow-200"
    : "text-red-600 bg-red-50 border-red-200";

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div className="border rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">GGM 기대수익률</div>
          <div className={`font-mono font-bold text-lg ${data.ggm_expected_return != null && data.ggm_expected_return >= 8 ? "text-green-600" : "text-orange-500"}`}>
            {data.ggm_expected_return != null ? `${data.ggm_expected_return.toFixed(2)}%` : "N/A"}
          </div>
          <div className="text-xs text-gray-400">요구수익률 기준 8%</div>
        </div>
        <div className="border rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">배당수익률 (D0/P)</div>
          <div className="font-mono font-bold text-lg text-indigo-600">
            {data.dividend_yield != null ? `${data.dividend_yield.toFixed(2)}%` : "N/A"}
          </div>
        </div>
        <div className="border rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">D0 (현재 DPS)</div>
          <div className="font-mono font-semibold">
            {data.d0 != null ? `${data.d0.toLocaleString("ko-KR")}원` : "N/A"}
          </div>
          <div className="text-xs text-gray-400">
            D1: {data.d1 != null ? `${data.d1.toLocaleString("ko-KR", { maximumFractionDigits: 0 })}원` : "N/A"}
          </div>
        </div>
        <div className="border rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">배당 성장률 (g)</div>
          <div className="font-mono font-semibold">
            {data.dividend_growth_rate != null ? `${data.dividend_growth_rate.toFixed(2)}%` : "N/A"}
          </div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-gray-600">배당 안정성</span>
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold font-mono">{score}<span className="text-sm font-normal text-gray-400">/100</span></span>
            {data.stability_grade && (
              <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${gradeColor}`}>{data.stability_grade}</span>
            )}
          </div>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-2">
          <div className={`h-2 rounded-full ${scoreBarColor}`} style={{ width: `${score}%` }} />
        </div>
      </div>

      {data.stability_detail && data.stability_detail.length > 0 && (
        <div className="space-y-1.5 border rounded-lg p-3">
          {data.stability_detail.map((item) => (
            <div key={item.name} className="flex items-start gap-3 text-sm">
              <div className={`w-8 text-right font-mono font-semibold flex-shrink-0 text-xs pt-0.5 ${item.score > 0 ? "text-green-600" : "text-gray-400"}`}>
                +{item.score}
              </div>
              <div className="flex-1">
                <span className="font-medium text-gray-700 text-xs">{item.name}</span>
                <span className="text-gray-400 text-xs ml-2">{item.reason}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className={`border rounded-lg px-4 py-3 text-sm ${verdictCls}`}>
        <span className="font-bold mr-2">{data.verdict}</span>
        <span className="text-xs">{data.verdict_reason}</span>
      </div>
    </div>
  );
}

function StrategyAnalysisSection({ code }: { code: string }) {
  const [strategyType, setStrategyType] = useState<"quant" | "dividend">("quant");
  const [result, setResult] = useState<StrategyAnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dartWarning, setDartWarning] = useState<string | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setDartWarning(null);
    try {
      const res = await api.getStrategyAnalysis(code, strategyType);
      setResult(res.data);
      setDartWarning(res.dart_warning ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "분석 실패");
    } finally {
      setLoading(false);
    }
  };

  const switchStrategy = (type: "quant" | "dividend") => {
    setStrategyType(type);
    setResult(null);
    setError(null);
    setDartWarning(null);
  };

  return (
    <div className="border rounded-lg p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">수익률 분석</h2>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border overflow-hidden text-sm">
            <button
              onClick={() => switchStrategy("quant")}
              className={`px-3 py-1.5 transition-colors ${strategyType === "quant" ? "bg-indigo-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
            >
              퀀트
            </button>
            <button
              onClick={() => switchStrategy("dividend")}
              className={`px-3 py-1.5 transition-colors ${strategyType === "dividend" ? "bg-indigo-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
            >
              배당
            </button>
          </div>
          <button
            onClick={runAnalysis}
            disabled={loading}
            className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "분석 중..." : "분석 실행"}
          </button>
        </div>
      </div>

      {!result && !loading && !error && (
        <p className="text-sm text-gray-400">
          {strategyType === "quant"
            ? "모멘텀(MA20·RSI) · 가치(PER·PBR) · 변동성 요인으로 퀀트 점수를 산출합니다."
            : "고든 성장 모델(GGM)로 기대수익률을 계산하고 배당 안정성을 점수화합니다. DART 재무 데이터를 조회합니다 (10~20초 소요)."}
        </p>
      )}

      {error && <div className="text-sm text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}

      {dartWarning && (
        <div className="text-xs text-orange-600 bg-orange-50 border border-orange-200 rounded px-3 py-2">
          DART 경고: {dartWarning}
        </div>
      )}

      {loading && (
        <div className="text-sm text-gray-400 py-6 text-center">
          {strategyType === "dividend" ? "DART 데이터 수집 중... (10~20초 소요)" : "분석 중..."}
        </div>
      )}

      {result && result.strategy_type === "quant" && <QuantResultView data={result} />}
      {result && result.strategy_type === "dividend" && <DividendResultView data={result} />}
    </div>
  );
}

const MAX_SCORE = 100;

const STRENGTH_STYLE: Record<string, string> = {
  "매우 강함": "bg-red-100 text-red-700",
  "강함":     "bg-orange-100 text-orange-700",
  "보통":     "bg-yellow-100 text-yellow-700",
  "약함":     "bg-gray-100 text-gray-500",
};

export default function StockDetailPage({ params }: { params: { code: string } }) {
  const { code } = params;
  const searchParams = useSearchParams();
  const from = searchParams.get("from");
  const fromSector = searchParams.get("sector");
  const backHref  = from === "portfolio" ? "/portfolio"
                  : from === "favorites" ? "/stocks?tab=favorites"
                  : from === "sector" && fromSector ? `/stocks?tab=sector&sector=${encodeURIComponent(fromSector)}`
                  : "/stocks";
  const backLabel = from === "portfolio" ? "← 포트폴리오"
                  : from === "favorites" ? "← 즐겨찾기"
                  : from === "sector" && fromSector ? `← ${fromSector}`
                  : "← 목록으로";
  const [detail, setDetail] = useState<StockDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toggle, isFavorite } = useFavorites();

  useEffect(() => {
    setError(null);
    api.getStockDetail(code)
      .then((res) => setDetail(res.data))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [code]);

  if (loading) return <div className="text-center py-20 text-gray-400">불러오는 중...</div>;
  if (error || !detail) return (
    <div className="text-center py-20 text-red-400">
      데이터를 가져올 수 없습니다.{error ? ` (${error})` : ""}
    </div>
  );

  const { metrics, ichimoku, technical, expected_return, current_price, change_rate, change_amount, volume, price_info, fetched_at } = detail;
  const { score, tags, signals, score_detail, strength, engine } = technical;
  const engineLabel = engine === "A" ? "추세 돌파형" : engine === "B" ? "역추세 반등형" : null;
  const scorePct = Math.min(100, Math.max(0, score / MAX_SCORE * 100));
  const scoreColor =
    score >= 75 ? "bg-red-500" : score >= 50 ? "bg-orange-400" : score >= 25 ? "bg-yellow-400" : "bg-blue-300";

  const priceUp = change_rate != null && change_rate >= 0;
  const priceColor = change_rate == null ? "text-gray-700" : priceUp ? "text-red-500" : "text-blue-500";

  return (
    <div className="space-y-6">
      <div>
        <Link href={backHref} className="text-sm text-blue-600 hover:underline mb-4 inline-block">
          {backLabel}
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold flex items-center gap-2 flex-wrap">
            {detail.stock_name}
            <span className="text-base font-normal text-gray-400">{code}</span>
            {detail.market && (
              <span className={`text-sm font-semibold px-2 py-0.5 rounded ${
                detail.market === "KOSPI"
                  ? "bg-blue-50 text-blue-600"
                  : "bg-emerald-50 text-emerald-600"
              }`}>
                {detail.market}
              </span>
            )}
          </h1>
          <button
            onClick={() => toggle(code, detail.stock_name)}
            className="p-1.5 rounded-full hover:bg-gray-100 transition-colors"
            title={isFavorite(code) ? "즐겨찾기 해제" : "즐겨찾기 추가"}
          >
            <Star className={`w-6 h-6 ${isFavorite(code) ? "fill-yellow-400 text-yellow-400" : "text-gray-300"}`} />
          </button>
          <a
            href={`https://finance.naver.com/item/main.naver?code=${code}`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-2.5 py-1 text-xs font-semibold rounded border border-green-400 text-green-600 hover:bg-green-50 transition-colors"
          >
            네이버 증권 ↗
          </a>
        </div>
      </div>

      {/* 현재가 */}
      <div className="border rounded-lg p-5 flex flex-wrap items-end gap-x-6 gap-y-2">
        <div>
          <div className="text-xs text-gray-500 mb-1">현재가</div>
          <div className={`text-3xl font-bold font-mono ${priceColor}`}>
            {current_price != null ? current_price.toLocaleString("ko-KR") : "N/A"}
          </div>
        </div>
        {change_rate != null && (
          <div className={`text-lg font-semibold font-mono ${priceColor}`}>
            {priceUp ? "▲" : "▼"} {Math.abs(change_amount ?? 0).toLocaleString("ko-KR")}
            <span className="ml-2 text-base">({priceUp ? "+" : ""}{change_rate.toFixed(2)}%)</span>
          </div>
        )}
        <div className="text-sm text-gray-400 ml-auto text-right">
          {volume != null && (
            <div>거래량 <span className="font-mono text-gray-600">{volume.toLocaleString("ko-KR")}</span></div>
          )}
          <div>기준시각 <span className="font-mono">{fetched_at} KST</span></div>
        </div>
      </div>

      {/* 기준 정보 */}
      <div className="border rounded-lg p-5">
        <h2 className="font-semibold mb-3 text-sm text-gray-600">주가 기준 정보</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-6 gap-y-2 text-sm">
          {[
            { label: "기준가(전일종가)", value: price_info.ref_price?.toLocaleString("ko-KR") },
            { label: "시가", value: price_info.open?.toLocaleString("ko-KR") },
            { label: "고가", value: price_info.high?.toLocaleString("ko-KR"), color: "text-red-500" },
            { label: "저가", value: price_info.low?.toLocaleString("ko-KR"), color: "text-blue-500" },
            { label: "상한가", value: price_info.upper_limit?.toLocaleString("ko-KR"), color: "text-red-400" },
            { label: "하한가", value: price_info.lower_limit?.toLocaleString("ko-KR"), color: "text-blue-400" },
            { label: "52주 최고", value: price_info.w52_high?.toLocaleString("ko-KR"), color: "text-red-500" },
            { label: "52주 최저", value: price_info.w52_low?.toLocaleString("ko-KR"), color: "text-blue-500" },
            {
              label: "시가총액",
              value: price_info.market_cap != null
                ? `${(price_info.market_cap / 10000).toFixed(1)}조`
                : undefined,
            },
            {
              label: "거래대금",
              value: price_info.trade_amount != null
                ? `${(price_info.trade_amount / 1_0000_0000).toFixed(0)}억`
                : undefined,
            },
            {
              label: "외국인 보유",
              value: price_info.foreign_rate != null ? `${price_info.foreign_rate.toFixed(2)}%` : undefined,
            },
            { label: "EPS", value: price_info.eps != null ? price_info.eps.toLocaleString("ko-KR") : undefined },
            { label: "BPS", value: price_info.bps != null ? price_info.bps.toLocaleString("ko-KR") : undefined },
          ].map(({ label, value, color }) => (
            <div key={label} className="flex justify-between border-b pb-1.5">
              <span className="text-gray-500">{label}</span>
              <span className={`font-mono font-medium ${color ?? "text-gray-800"}`}>{value ?? "N/A"}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 기본 지표 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "PER", value: (metrics.per != null && metrics.per > 0) ? `${metrics.per.toFixed(1)}` : "N/A" },
          { label: "PBR", value: metrics.pbr?.toFixed(2) ?? "N/A" },
          { label: "ROE", value: metrics.roe ? `${metrics.roe.toFixed(1)}%` : "N/A" },
        ].map(({ label, value }) => (
          <div key={label} className="border rounded-lg p-4">
            <div className="text-xs text-gray-500 mb-1">{label}</div>
            <div className="text-xl font-semibold">{value}</div>
          </div>
        ))}
        <div className="border rounded-lg p-4">
          <div className="text-xs text-gray-500 mb-1">구름 위치</div>
          <div className="mt-1"><CloudBadge position={ichimoku.position} /></div>
        </div>
      </div>

      {/* 기대 수익률 분석 */}
      {expected_return && <ExpectedReturnSection er={expected_return} />}

      {/* 퀀트/배당 수익률 분석 */}
      <StrategyAnalysisSection code={code} />

      {/* 기술적 분석 스코어 */}
      <div className="border rounded-lg p-5">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <h2 className="font-semibold">기술적 분석</h2>
            {engineLabel && (
              <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${
                engine === "A" ? "bg-orange-100 text-orange-700" : "bg-sky-100 text-sky-700"
              }`}>
                {engine === "A" ? "⬆" : "↩"} {engineLabel}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${STRENGTH_STYLE[strength] ?? STRENGTH_STYLE["약함"]}`}>
              {strength}
            </span>
            <span className="text-2xl font-bold">
              {score}
              <span className="text-sm text-gray-400 font-normal"> / {MAX_SCORE}</span>
            </span>
          </div>
        </div>

        {/* 전체 점수 바 */}
        <div className="w-full bg-gray-100 rounded-full h-2 mb-4">
          <div className={`h-2 rounded-full transition-all ${scoreColor}`} style={{ width: `${scorePct}%` }} />
        </div>

        {/* 듀얼 엔진 점수 */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <CategoryBar
            label="Engine A — 추세 돌파형"
            score={score_detail.engine_a ?? 0}
            max={100}
            color={engine === "A" ? "bg-orange-400" : "bg-gray-300"}
          />
          <CategoryBar
            label="Engine B — 역추세 반등형"
            score={score_detail.engine_b ?? 0}
            max={100}
            color={engine === "B" ? "bg-sky-400" : "bg-gray-300"}
          />
        </div>

        {/* 매수 신호 태그 */}
        {tags.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <span key={tag} className="bg-blue-50 text-blue-700 text-xs px-2.5 py-1 rounded-full font-medium">
                {tag}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">활성 신호 없음</p>
        )}
      </div>

      {/* 기술적 지표 상세 */}
      <div className="border rounded-lg p-5">
        <h2 className="font-semibold mb-4">기술적 지표</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">

          {/* A. 추세 */}
          <div className="sm:col-span-2 text-xs font-semibold text-indigo-500 uppercase tracking-wide pt-1">A. 추세 지표</div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">MA5 / MA20 / MA60</span>
            <span className="font-mono text-gray-700">
              {fmt(signals.ma5)} / {fmt(signals.ma20)} / {fmt(signals.ma60)}
            </span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">MACD</span>
            <span className={`font-mono font-semibold ${signals.macd != null && signals.macd > 0 ? "text-red-500" : "text-blue-500"}`}>
              {signals.macd != null ? fmt(signals.macd, 0) : "N/A"}
              {signals.macd_signal != null && (
                <span className="text-gray-400 font-normal text-xs ml-1">
                  (Signal: {fmt(signals.macd_signal, 0)})
                </span>
              )}
            </span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">이격도 (MA20)</span>
            <span className={`font-mono font-semibold ${
              signals.disparity != null && signals.disparity < 97 ? "text-blue-500"
              : signals.disparity != null && signals.disparity > 107 ? "text-red-500"
              : "text-gray-700"
            }`}>
              {signals.disparity != null ? `${signals.disparity.toFixed(1)}%` : "N/A"}
            </span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">DMI +DI / -DI</span>
            <span className="font-mono">
              <span className="text-red-500">{signals.plus_di != null ? signals.plus_di.toFixed(1) : "N/A"}</span>
              {" / "}
              <span className="text-blue-500">{signals.minus_di != null ? signals.minus_di.toFixed(1) : "N/A"}</span>
            </span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">ADX</span>
            <AdxLabel adx={signals.adx} plusDi={signals.plus_di} minusDi={signals.minus_di} />
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">Parabolic SAR</span>
            <span className={`font-mono font-semibold ${signals.parabolic_sar != null ? "text-gray-700" : ""}`}>
              {signals.parabolic_sar != null ? fmt(signals.parabolic_sar, 0) : "N/A"}
            </span>
          </div>

          {/* B. 모멘텀 */}
          <div className="sm:col-span-2 text-xs font-semibold text-green-600 uppercase tracking-wide pt-2">B. 모멘텀 지표</div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">RSI (14)</span>
            <RsiBar value={signals.rsi} />
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">스토캐스틱 %K / %D</span>
            <span className="font-mono">
              {signals.stoch_k != null ? signals.stoch_k.toFixed(1) : "N/A"}
              {" / "}
              {signals.stoch_d != null ? signals.stoch_d.toFixed(1) : "N/A"}
            </span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">CCI (20)</span>
            <CciLabel value={signals.cci} />
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">MFI (14)</span>
            <MfiLabel value={signals.mfi} />
          </div>

          {/* C. 변동성 */}
          <div className="sm:col-span-2 text-xs font-semibold text-yellow-600 uppercase tracking-wide pt-2">C. 변동성 / 가격패턴</div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">볼린저 상단 / 하단</span>
            <span className="font-mono text-gray-700">
              {fmt(signals.bb_upper)} / {fmt(signals.bb_lower)}
            </span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">볼린저 밴드폭 (%)</span>
            <span className={`font-mono font-semibold ${
              signals.bb_bandwidth != null && signals.bb_bandwidth < 10 ? "text-orange-500" : "text-gray-700"
            }`}>
              {signals.bb_bandwidth != null ? `${signals.bb_bandwidth.toFixed(1)}%` : "N/A"}
              {signals.bb_bandwidth != null && signals.bb_bandwidth < 10 && (
                <span className="text-xs font-normal ml-1">(스퀴즈)</span>
              )}
            </span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">ATR (14)</span>
            <span className="font-mono text-gray-700">{signals.atr != null ? fmt(signals.atr, 0) : "N/A"}</span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">엔벨로프 상단 / 하단</span>
            <span className="font-mono text-gray-700">
              {fmt(signals.env_upper)} / {fmt(signals.env_lower)}
            </span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">피봇 S2</span>
            <span className="font-mono text-gray-700">{fmt(signals.pivot_s2)}</span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">피보나치 지지</span>
            {signals.fib_level != null && signals.fib_ratio != null ? (
              <span className={`font-mono font-semibold ${signals.fib_ratio === 0.618 ? "text-purple-600" : "text-indigo-500"}`}>
                {fmt(signals.fib_level)}
                <span className="text-xs font-normal ml-1">({(signals.fib_ratio * 100).toFixed(1)}% 되돌림)</span>
              </span>
            ) : (
              <span className="text-gray-400 font-mono text-xs">
                {signals.fib_reason ?? "해당 없음"}
              </span>
            )}
          </div>

          {/* D. 거래량 */}
          <div className="sm:col-span-2 text-xs font-semibold text-orange-500 uppercase tracking-wide pt-2">D. 거래량 / 매집</div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">거래량 MA20</span>
            <span className="font-mono text-gray-700">{signals.volume_ma20 != null ? fmt(signals.volume_ma20, 0) : "N/A"}</span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">거래량 비율 (vs MA20)</span>
            <span className={`font-mono font-semibold ${
              signals.volume_ratio != null && signals.volume_ratio >= 2 ? "text-red-500"
              : signals.volume_ratio != null && signals.volume_ratio >= 1.5 ? "text-orange-500"
              : "text-gray-700"
            }`}>
              {signals.volume_ratio != null ? `${signals.volume_ratio.toFixed(2)}x` : "N/A"}
            </span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">OBV</span>
            <span className="font-mono text-gray-700">{signals.obv != null ? fmt(signals.obv, 0) : "N/A"}</span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">VR (20)</span>
            <span className={`font-mono font-semibold ${
              signals.vr != null && signals.vr < 70 ? "text-blue-500"
              : signals.vr != null && signals.vr > 150 ? "text-red-500"
              : "text-gray-700"
            }`}>
              {signals.vr != null ? signals.vr.toFixed(1) : "N/A"}
              {signals.vr != null && signals.vr < 70 && <span className="text-xs font-normal ml-1">(과매도)</span>}
            </span>
          </div>

          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-500">Chaikin Oscillator</span>
            <span className={`font-mono font-semibold ${
              signals.chaikin_osc != null && signals.chaikin_osc > 0 ? "text-red-500"
              : signals.chaikin_osc != null && signals.chaikin_osc < 0 ? "text-blue-500"
              : "text-gray-700"
            }`}>
              {signals.chaikin_osc != null ? signals.chaikin_osc.toFixed(0) : "N/A"}
            </span>
          </div>

        </div>
      </div>

      {/* 일목균형표 */}
      <div className="border rounded-lg p-5">
        <h2 className="font-semibold mb-4">일목균형표</h2>
        <div className="grid grid-cols-2 gap-3 text-sm">
          {[
            { label: "전환선", value: ichimoku.conversion_line },
            { label: "기준선", value: ichimoku.base_line },
            { label: "선행스팬A", value: ichimoku.span_a },
            { label: "선행스팬B", value: ichimoku.span_b },
          ].map(({ label, value }) => (
            <div key={label} className="flex justify-between border-b pb-2">
              <span className="text-gray-500">{label}</span>
              <span className="font-mono">{value.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
