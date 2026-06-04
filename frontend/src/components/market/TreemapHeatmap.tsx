"use client";
import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/components/AuthProvider";
import { MarketStock, SparklinePoint } from "@/lib/types";

type SortBy = "change_rate" | "frgn_net_buy" | "org_net_buy";
type ViewMode = "top100" | "sector";

interface Tile extends MarketStock {
  x: number; y: number; w: number; h: number;
}

interface SectorBox {
  x: number; y: number; w: number; h: number;
  sector: string;
  stocks: MarketStock[];
  totalMarketCap: number;
}

// ── 스쿼리파이드 트리맵 알고리즘 ──────────────────────────────────────────────

function squarify<T extends { value: number }>(
  items: T[], rx: number, ry: number, rw: number, rh: number
): (T & { x: number; y: number; w: number; h: number })[] {
  const sorted = [...items].filter(i => i.value > 0).sort((a, b) => b.value - a.value);
  if (sorted.length === 0) return [];
  const totalValue = sorted.reduce((s, i) => s + i.value, 0);
  const result: (T & { x: number; y: number; w: number; h: number })[] = [];

  function layout(rem: T[], x: number, y: number, w: number, h: number, remVal: number) {
    if (rem.length === 0 || w < 0.5 || h < 0.5) return;
    const horiz = w >= h;
    const shortSide = horiz ? h : w;

    let row: T[] = [];
    let rowVal = 0;
    let prevWorst = Infinity;
    let cut = 0;

    for (let i = 0; i < rem.length; i++) {
      const item = rem[i];
      const testVal = rowVal + item.value;
      const testRow = [...row, item];
      const rowArea = (testVal / remVal) * w * h;
      const depth = rowArea / shortSide;
      let worst = 0;
      for (const it of testRow) {
        const cross = (it.value / testVal) * shortSide;
        const r = depth > cross ? depth / cross : cross / depth;
        if (r > worst) worst = r;
      }
      if (worst > prevWorst && row.length > 0) break;
      row = testRow;
      rowVal = testVal;
      prevWorst = worst;
      cut = i + 1;
    }

    if (row.length === 0) { row = [rem[0]]; rowVal = rem[0].value; cut = 1; }

    const rowArea = (rowVal / remVal) * w * h;
    const depth = rowArea / shortSide;
    let offset = 0;
    for (const item of row) {
      const cross = (item.value / rowVal) * shortSide;
      if (horiz) {
        result.push({ ...item, x, y: y + offset, w: depth, h: cross });
      } else {
        result.push({ ...item, x: x + offset, y, w: cross, h: depth });
      }
      offset += cross;
    }

    if (cut < rem.length) {
      const nextVal = remVal - rowVal;
      if (horiz) layout(rem.slice(cut), x + depth, y, w - depth, h, nextVal);
      else layout(rem.slice(cut), x, y + depth, w, h - depth, nextVal);
    }
  }

  layout(sorted, rx, ry, rw, rh, totalValue);
  return result;
}

// ── 색상 스케일 ───────────────────────────────────────────────────────────────

function rateColor(rate: number): string {
  if (rate >= 3) return "#7f1d1d";
  if (rate >= 2) return "#991b1b";
  if (rate >= 1) return "#dc2626";
  if (rate >= 0.3) return "#ef4444";
  if (rate > -0.3) return "#6b7280";
  if (rate > -1) return "#3b82f6";
  if (rate > -2) return "#2563eb";
  if (rate > -3) return "#1d4ed8";
  return "#1e3a8a";
}

function textColor(rate: number): string {
  return Math.abs(rate) < 0.3 ? "#f9fafb" : "#ffffff";
}

// ── 스파크라인 SVG ────────────────────────────────────────────────────────────

function Sparkline({ data, color }: { data: SparklinePoint[]; color: string }) {
  if (data.length < 2) return null;
  const values = data.map(d => d.close);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const W = 96, H = 36;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * W},${H - ((v - min) / range) * H}`).join(" ");
  return (
    <svg width={W} height={H} className="block">
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────────

export default function TreemapHeatmap() {
  const session = useSession();
  const router = useRouter();
  const [stocks, setStocks] = useState<MarketStock[]>([]);
  const [sortBy, setSortBy] = useState<SortBy>("change_rate");
  const [viewMode, setViewMode] = useState<ViewMode>("sector");
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; stock: MarketStock } | null>(null);
  const [sparkline, setSparkline] = useState<SparklinePoint[]>([]);
  const [dims, setDims] = useState({ w: 1200, h: 580 });
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  // Responsive width
  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver(entries => {
      const w = entries[0].contentRect.width;
      if (w > 100) setDims({ w, h: Math.max(460, Math.min(w * 0.52, 680)) });
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (!session) return; // 세션 없으면 대기
    setLoading(true);
    setFetchError(null);
    api.getMarketTreemap(sortBy)
      .then(res => {
        setStocks(res.data || []);
        setLoading(false);
      })
      .catch(err => {
        setFetchError(err.message || "데이터 조회 실패");
        setLoading(false);
      });
  }, [sortBy, session]);

  // ── 레이아웃 계산 ──────────────────────────────────────────────────────────

  const { tiles, sectorBoxes } = useMemo<{ tiles: Tile[]; sectorBoxes: SectorBox[] }>(() => {
    if (stocks.length === 0) return { tiles: [], sectorBoxes: [] };
    const { w, h } = dims;

    if (viewMode === "top100") {
      const top = [...stocks].filter(s => s.market_cap > 0).sort((a, b) => b.market_cap - a.market_cap).slice(0, 100);
      const items = top.map(s => ({ ...s, value: s.market_cap }));
      const laid = squarify(items, 0, 0, w, h);
      return { tiles: laid as Tile[], sectorBoxes: [] };
    }

    // Sector hierarchy
    const sectorMap = new Map<string, MarketStock[]>();
    for (const s of stocks) {
      if (!sectorMap.has(s.sector)) sectorMap.set(s.sector, []);
      sectorMap.get(s.sector)!.push(s);
    }
    const sectorItems = Array.from(sectorMap.entries()).map(([sector, ss]) => ({
      sector, stocks: ss,
      totalMarketCap: ss.reduce((sum, s) => sum + (s.market_cap || 0), 0),
      value: ss.reduce((sum, s) => sum + (s.market_cap || 0), 0),
    })).filter(si => si.value > 0);

    const LABEL_H = 18;
    const PAD = 2;
    const sBoxes = squarify(sectorItems, 0, 0, w, h);
    const boxes: SectorBox[] = sBoxes.map(sb => ({ ...sb }));

    const allTiles: Tile[] = [];
    for (const box of sBoxes) {
      const innerX = box.x + PAD;
      const innerY = box.y + LABEL_H;
      const innerW = box.w - PAD * 2;
      const innerH = box.h - LABEL_H - PAD;
      if (innerW < 4 || innerH < 4) continue;
      const stockItems = box.stocks.filter(s => s.market_cap > 0).map(s => ({ ...s, value: s.market_cap }));
      const laid = squarify(stockItems, innerX, innerY, innerW, innerH);
      for (const t of laid) {
        allTiles.push(t as Tile);
      }
    }

    return { tiles: allTiles, sectorBoxes: boxes };
  }, [stocks, viewMode, dims]);

  // ── 툴팁 ──────────────────────────────────────────────────────────────────

  const handleMouseEnter = useCallback((stock: MarketStock, e: React.MouseEvent) => {
    setTooltip({ x: e.clientX, y: e.clientY, stock });
    setSparkline([]);
    if (tooltipDebounce.current) clearTimeout(tooltipDebounce.current);
    tooltipDebounce.current = setTimeout(async () => {
      const res = await api.getSparkline(stock.stock_code, 5);
      setSparkline(res.data || []);
    }, 300);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
    if (tooltipDebounce.current) clearTimeout(tooltipDebounce.current);
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (tooltip) setTooltip(prev => prev ? { ...prev, x: e.clientX, y: e.clientY } : null);
  }, [tooltip]);

  // ── 렌더 ──────────────────────────────────────────────────────────────────

  const tooltipEl = tooltip && mounted ? createPortal(
    <div
      className="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-xl p-3 text-xs pointer-events-none"
      style={{ left: tooltip.x + 14, top: Math.min(tooltip.y - 10, window.innerHeight - 200), minWidth: 150 }}
    >
      <div className="font-bold text-sm mb-1 text-gray-900">{tooltip.stock.stock_name}</div>
      <div className="text-gray-400 mb-2">{tooltip.stock.stock_code} · {tooltip.stock.sector}</div>
      <div className={`text-base font-bold mb-2 ${tooltip.stock.change_rate > 0 ? "text-red-600" : tooltip.stock.change_rate < 0 ? "text-blue-600" : "text-gray-500"}`}>
        {tooltip.stock.change_rate > 0 ? "+" : ""}{tooltip.stock.change_rate.toFixed(2)}%
      </div>
      {sparkline.length > 1 && (
        <div className="mb-2">
          <Sparkline data={sparkline} color={tooltip.stock.change_rate >= 0 ? "#ef4444" : "#3b82f6"} />
          <div className="text-gray-400 mt-0.5">최근 {sparkline.length}일 종가</div>
        </div>
      )}
      <div className="space-y-0.5 text-gray-600">
        <div>현재가: <span className="font-medium text-gray-900">{tooltip.stock.current_price.toLocaleString()}원</span></div>
        <div>시총: <span className="font-medium text-gray-900">{(tooltip.stock.market_cap / 10000).toFixed(0)}조원</span></div>
        {tooltip.stock.frgn_ntby_qty !== 0 && (
          <div>외국인 순매수: <span className={`font-medium ${tooltip.stock.frgn_ntby_qty > 0 ? "text-red-600" : "text-blue-600"}`}>{tooltip.stock.frgn_ntby_qty > 0 ? "+" : ""}{tooltip.stock.frgn_ntby_qty.toLocaleString()}주</span></div>
        )}
        {tooltip.stock.org_ntby_qty !== 0 && (
          <div>기관 순매수: <span className={`font-medium ${tooltip.stock.org_ntby_qty > 0 ? "text-red-600" : "text-blue-600"}`}>{tooltip.stock.org_ntby_qty > 0 ? "+" : ""}{tooltip.stock.org_ntby_qty.toLocaleString()}주</span></div>
        )}
      </div>
    </div>,
    document.body
  ) : null;

  return (
    <div className="space-y-3">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex rounded-lg border overflow-hidden text-sm">
          {([["sector", "섹터별"], ["top100", "KOSPI Top 100"]] as [ViewMode, string][]).map(([m, label]) => (
            <button key={m} onClick={() => setViewMode(m)}
              className={`px-3 py-1.5 ${viewMode === m ? "bg-blue-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}>
              {label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1 text-sm">
          <span className="text-gray-500 text-xs">정렬:</span>
          <select value={sortBy} onChange={e => setSortBy(e.target.value as SortBy)}
            className="border rounded px-2 py-1 text-xs text-gray-700 bg-white">
            <option value="change_rate">등락률</option>
            <option value="frgn_net_buy">외국인 순매수</option>
            <option value="org_net_buy">기관 순매수</option>
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs ml-auto">
          {[["진한 빨강", "#7f1d1d", "+3%"], ["빨강", "#ef4444", "+1%"], ["회색", "#6b7280", "0%"], ["파랑", "#3b82f6", "-1%"], ["진한 파랑", "#1e3a8a", "-3%"]].map(([, color, label]) => (
            <span key={label} className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-sm inline-block" style={{ background: color }} />
              <span className="text-gray-500">{label}</span>
            </span>
          ))}
        </div>
      </div>

      {/* Treemap */}
      <div ref={containerRef} className="relative w-full rounded-lg overflow-hidden bg-gray-900">
        {fetchError ? (
          <div className="flex flex-col items-center justify-center h-96 gap-2">
            <div className="text-red-400 text-sm">{fetchError}</div>
            <button onClick={() => { setFetchError(null); setLoading(true); api.getMarketTreemap(sortBy).then(r => { setStocks(r.data || []); setLoading(false); }).catch(e => { setFetchError(e.message); setLoading(false); }); }}
              className="text-xs text-blue-400 underline">재시도</button>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center h-96 text-gray-400 text-sm animate-pulse">
            종목 데이터 로딩 중… (약 20초 소요)
          </div>
        ) : tiles.length === 0 ? (
          <div className="flex items-center justify-center h-96 text-gray-400 text-sm">
            데이터를 불러올 수 없습니다
          </div>
        ) : (
          <svg
            width={dims.w} height={dims.h}
            className="block"
            onMouseMove={handleMouseMove}
          >
            {/* Sector background boxes */}
            {sectorBoxes.map(sb => (
              <g key={`sb-${sb.sector}`}>
                <rect x={sb.x} y={sb.y} width={sb.w} height={sb.h}
                  fill="transparent" stroke="#374151" strokeWidth={1} />
                {sb.w > 50 && (
                  <text x={sb.x + 4} y={sb.y + 13}
                    fill="#d1d5db" fontSize={11} fontWeight="600"
                    style={{ pointerEvents: "none", userSelect: "none" }}>
                    {sb.sector.length > 12 ? sb.sector.slice(0, 11) + "…" : sb.sector}
                  </text>
                )}
              </g>
            ))}

            {/* Stock tiles */}
            {tiles.map(tile => {
              const color = rateColor(tile.change_rate);
              const fgColor = textColor(tile.change_rate);
              const showName = tile.w > 36 && tile.h > 18;
              const showCode = tile.w > 36 && tile.h > 32;
              const showRate = tile.w > 44 && tile.h > 48;
              const fontSize = Math.min(tile.w / 6, tile.h / 4, 13);
              const lineH = Math.max(fontSize * 1.25, 9);
              const lines = [showName, showCode, showRate].filter(Boolean).length;
              const startY = tile.y + tile.h / 2 - ((lines - 1) * lineH) / 2;
              let lineIdx = 0;

              return (
                <g key={tile.stock_code}
                  onClick={() => router.push(`/stocks/${tile.stock_code}`)}
                  onMouseEnter={e => handleMouseEnter(tile, e)}
                  onMouseLeave={handleMouseLeave}
                  style={{ cursor: "pointer" }}>
                  <rect
                    x={tile.x + 0.5} y={tile.y + 0.5}
                    width={Math.max(tile.w - 1, 0)} height={Math.max(tile.h - 1, 0)}
                    fill={color} rx={2}
                  />
                  {showName && (
                    <text
                      x={tile.x + tile.w / 2} y={startY + lineH * lineIdx++}
                      textAnchor="middle" dominantBaseline="central"
                      fill={fgColor} fontSize={Math.max(fontSize, 8)}
                      fontWeight="600" style={{ pointerEvents: "none", userSelect: "none" }}>
                      {tile.stock_name.length > 7 ? tile.stock_name.slice(0, 6) + "…" : tile.stock_name}
                    </text>
                  )}
                  {showCode && (
                    <text
                      x={tile.x + tile.w / 2} y={startY + lineH * lineIdx++}
                      textAnchor="middle" dominantBaseline="central"
                      fill={fgColor} fontSize={Math.max(fontSize * 0.8, 7)}
                      style={{ pointerEvents: "none", userSelect: "none", opacity: 0.75 }}>
                      ({tile.stock_code})
                    </text>
                  )}
                  {showRate && (
                    <text
                      x={tile.x + tile.w / 2} y={startY + lineH * lineIdx++}
                      textAnchor="middle" dominantBaseline="central"
                      fill={fgColor} fontSize={Math.max(fontSize * 0.85, 7)}
                      style={{ pointerEvents: "none", userSelect: "none", opacity: 0.9 }}>
                      {tile.change_rate > 0 ? "+" : ""}{tile.change_rate.toFixed(2)}%
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        )}
      </div>

      {tooltipEl}
    </div>
  );
}
