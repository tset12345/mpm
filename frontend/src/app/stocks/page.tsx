"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { StockSummary, StockMaster, SectorLeaderStock } from "@/lib/types";
import { useFavorites } from "@/hooks/useFavorites";
import { RefreshCw, Search, Star, X, TrendingUp } from "lucide-react";

function ScoreBadge({ tech, fund, total }: { tech?: number; fund?: number; total?: number }) {
  const display = total ?? tech;
  if (display == null) return null;
  const color =
    display >= 75 ? "bg-red-100 text-red-700" :
    display >= 50 ? "bg-orange-100 text-orange-700" :
    display >= 25 ? "bg-yellow-100 text-yellow-700" :
    "bg-gray-100 text-gray-500";

  const hasFund = fund != null && fund > 0;
  const tooltip = hasFund
    ? `기술 ${tech ?? 0}점 + 리포트 ${fund}점 = 합산 ${total ?? display}점`
    : `기술 점수 ${display}점`;

  return (
    <span className="inline-flex items-center gap-1" title={tooltip}>
      <span className={`text-xs font-bold px-2 py-0.5 rounded font-mono ${color}`}>
        {display}
      </span>
      {hasFund && (
        <span className="text-xs text-emerald-600 font-semibold" title={`리포트 +${fund}점`}>
          +{fund}📄
        </span>
      )}
    </span>
  );
}

const SOURCE_STYLE: Record<string, string> = {
  "거래대금": "bg-slate-100 text-slate-600",
  "기관외인": "bg-violet-100 text-violet-700",
  "거래량":   "bg-sky-100 text-sky-700",
  "신고가":   "bg-amber-100 text-amber-700",
  "VI발동":   "bg-rose-100 text-rose-700",
};

function SourceBadges({ sources }: { sources?: string[] }) {
  if (!sources?.length) return null;
  return (
    <div className="flex gap-0.5 flex-wrap mt-0.5">
      {sources.map((s) => (
        <span key={s} className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${SOURCE_STYLE[s] ?? "bg-gray-100 text-gray-500"}`}>
          {s}
        </span>
      ))}
    </div>
  );
}

function formatGeneratedAt(iso: string): string {
  try {
    const d = new Date(iso);
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    const hh = String(d.getHours()).padStart(2, "0");
    const min = String(d.getMinutes()).padStart(2, "0");
    return `${mm}/${dd} ${hh}:${min}`;
  } catch {
    return iso;
  }
}

function EntryPriceBadge({ entry, current, consecutiveDays }: { entry?: number | null; current?: number | null; consecutiveDays?: number }) {
  if (!entry) return <span className="text-gray-300">-</span>;
  const label = consecutiveDays && consecutiveDays > 1 ? "최초" : "추천가";
  if (!current || current === entry) {
    return (
      <span className="font-mono text-gray-500 text-xs" title={label}>
        {entry.toLocaleString()}
      </span>
    );
  }
  const diff = current - entry;
  const pct = ((diff / entry) * 100).toFixed(1);
  const positive = diff > 0;
  return (
    <span className="flex flex-col items-end" title={`${label}: ${entry.toLocaleString()}원`}>
      <span className="font-mono text-gray-500 text-xs">{entry.toLocaleString()}</span>
      <span className={`font-mono text-xs font-semibold ${positive ? "text-red-500" : "text-blue-500"}`}>
        {positive ? "+" : ""}{pct}%
      </span>
    </span>
  );
}

function ConsecutiveBadge({ days }: { days: number | undefined }) {
  if (!days || days < 2) return null;
  const color =
    days >= 5 ? "bg-purple-100 text-purple-700" :
    days >= 3 ? "bg-indigo-100 text-indigo-700" :
    "bg-teal-100 text-teal-700";
  return (
    <span className={`inline-block text-xs font-semibold px-1.5 py-0.5 rounded ${color}`} title={`${days}일 연속 추천`}>
      🔁 {days}일
    </span>
  );
}

const SECTORS = [
  "반도체(AI/HBM)", "온디바이스 AI", "2차전지 소재·장비", "로봇·스마트팩토리",
  "우주항공·방산", "자율주행·전장부품", "바이오시밀러·신약", "양자컴퓨터·원자력(SMR)",
  "자동차 제조", "조선·해양플랜트", "철강·비철금속", "화학·정유",
  "디스플레이·OLED", "기계·건설장비", "인터넷·엔터테인먼트", "게임·콘텐츠",
  "금융(은행·보험·증권)", "음식료", "화장품·미용기기", "신재생 에너지",
];

export default function StocksPage() {
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<"recommend" | "favorites" | "sector">(
    searchParams.get("tab") === "favorites" ? "favorites" :
    searchParams.get("tab") === "sector" ? "sector" : "recommend"
  );
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [sectorLeaders, setSectorLeaders] = useState<SectorLeaderStock[]>([]);
  const [sectorUpdatedAt, setSectorUpdatedAt] = useState<string | null>(null);
  const [allSectorLeaders, setAllSectorLeaders] = useState<{ sector: string; leaders: SectorLeaderStock[]; updated_at: string | null }[]>([]);
  const [allSectorProgress, setAllSectorProgress] = useState(0);
  const [sectorLoading, setSectorLoading] = useState(false);
  const [sectorRefreshing, setSectorRefreshing] = useState(false);
  const [stocks, setStocks] = useState<StockSummary[]>([]);
  const [dataDate, setDataDate] = useState<string | null>(null);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [priceUpdatedAt, setPriceUpdatedAt] = useState<Date | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<StockMaster[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [extraFavoriteData, setExtraFavoriteData] = useState<StockSummary[]>([]);
  const [extraFavoritesLoading, setExtraFavoritesLoading] = useState(false);
  const { favorites, toggle, isFavorite } = useFavorites();
  const router = useRouter();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshRecommendations = () => {
    if (refreshing) return;
    setRefreshing(true);
    api.getRecommendations()
      .then((res) => {
        setStocks(res.data ?? []);
        setDataDate(res.date ?? null);
        setGeneratedAt(res.generated_at ?? null);
        refreshPrices();
      })
      .catch(() => {})
      .finally(() => setRefreshing(false));
  };

  const refreshPrices = () => {
    api.getRecommendationPrices().then((res) => {
      if (!res.data?.length) return;
      const map = Object.fromEntries(res.data.map((p) => [p.stock_code, p]));
      setStocks((prev) =>
        prev.map((s) =>
          map[s.stock_code]
            ? {
                ...s,
                current_price: map[s.stock_code].current_price ?? s.current_price,
                change_rate:   map[s.stock_code].change_rate   ?? s.change_rate,
              }
            : s
        )
      );
      setPriceUpdatedAt(new Date());
    }).catch(() => {});
  };

  useEffect(() => {
    setLoading(true);
    api.getRecommendations()
      .then((res) => {
        setStocks(res.data ?? []);
        setDataDate(res.date ?? null);
        setGeneratedAt(res.generated_at ?? null);
        // 초기 로드 직후 실시간 가격 즉시 반영
        refreshPrices();
      })
      .catch(() => setStocks([]))
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 30초마다 현재가·등락률 자동 갱신
  useEffect(() => {
    if (loading) return;
    pollRef.current = setInterval(refreshPrices, 30_000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [loading]); // eslint-disable-line react-hooks/exhaustive-deps

  // 추천 목록에 없는 즐겨찾기 종목 상세 조회
  useEffect(() => {
    if (loading) return;
    const extraCodes = favorites.filter(
      (code) => !stocks.some((s) => s.stock_code === code)
    );
    if (extraCodes.length === 0) {
      setExtraFavoriteData([]);
      return;
    }
    setExtraFavoritesLoading(true);
    Promise.allSettled(extraCodes.map((code) => api.getStockDetail(code)))
      .then((results) => {
        const mapped: StockSummary[] = results
          .filter(
            (r): r is PromiseFulfilledResult<{ status: string; data: import("@/lib/types").StockDetail }> =>
              r.status === "fulfilled"
          )
          .map((r) => {
            const d = r.value.data;
            return {
              stock_code: d.stock_code,
              stock_name: d.stock_name,
              current_price: d.current_price,
              change_rate: d.change_rate,
              volume: d.volume,
              tags: d.technical.tags,
              tech_score: d.technical.score,
            };
          });
        setExtraFavoriteData(mapped);
      })
      .finally(() => setExtraFavoritesLoading(false));
  }, [favorites.join(","), loading]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    setSearchLoading(true);
    const timer = setTimeout(() => {
      api.searchStocks(searchQuery.trim())
        .then((res) => setSearchResults(res.data ?? []))
        .catch(() => setSearchResults([]))
        .finally(() => setSearchLoading(false));
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const favoriteStocks = stocks
    .filter((s) => isFavorite(s.stock_code))
    .sort((a, b) => (b.total_score ?? b.tech_score ?? 0) - (a.total_score ?? a.tech_score ?? 0));
  const allFavorites = [...favoriteStocks, ...extraFavoriteData];
  const displayed = tab === "recommend" ? stocks : allFavorites;

  const isSearchMode = searchQuery.trim().length > 0;
  const favoritesLoading = loading || extraFavoritesLoading;

  function StockTable({ rows, fromTab }: { rows: StockSummary[]; fromTab?: string }) {
    return (
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th className="px-4 py-3 text-left w-56">종목명</th>
              <th className="px-4 py-3 text-right">현재가</th>
              <th className="px-4 py-3 text-right">등락률</th>
              <th className="px-4 py-3 text-right">추천가</th>
              <th className="px-4 py-3 text-right">거래량</th>
              <th className="px-4 py-3 text-right">분석점수</th>
              <th className="px-4 py-3 text-left">태그</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {rows.map((s) => (
              <tr
                key={s.stock_code}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => router.push(`/stocks/${s.stock_code}${fromTab ? `?from=${fromTab}` : ""}`)}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium">{s.stock_name}</span>
                    <ConsecutiveBadge days={s.consecutive_days} />
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-400">
                    <span>{s.stock_code}</span>
                    {s.market && (
                      <span className={`px-1.5 py-0.5 rounded font-semibold ${
                        s.market === "KOSPI"
                          ? "bg-blue-50 text-blue-600"
                          : "bg-emerald-50 text-emerald-600"
                      }`}>
                        {s.market}
                      </span>
                    )}
                  </div>
                  <SourceBadges sources={s.source_conditions} />
                </td>
                <td className="px-4 py-3 text-right font-mono">{s.current_price?.toLocaleString() ?? "-"}</td>
                <td className={`px-4 py-3 text-right font-mono ${(s.change_rate ?? 0) >= 0 ? "text-red-500" : "text-blue-500"}`}>
                  {s.change_rate != null ? `${s.change_rate >= 0 ? "+" : ""}${s.change_rate.toFixed(2)}%` : "-"}
                </td>
                <td className="px-4 py-3 text-right">
                  <EntryPriceBadge entry={s.first_entry_price} current={s.current_price} consecutiveDays={s.consecutive_days} />
                </td>
                <td className="px-4 py-3 text-right font-mono text-gray-500">{s.volume?.toLocaleString() ?? "-"}</td>
                <td className="px-4 py-3 text-right">
                  <ScoreBadge tech={s.tech_score} fund={s.fund_score} total={s.total_score} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1 flex-wrap">
                    {(s.tags ?? []).map((tag) => (
                      <span key={tag} className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full">{tag}</span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3" onClick={(e) => { e.stopPropagation(); toggle(s.stock_code); }}>
                  <Star className={`w-4 h-4 ${isFavorite(s.stock_code) ? "fill-yellow-400 text-yellow-400" : "text-gray-300"}`} />
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-12 text-center text-gray-400">표시할 종목이 없습니다.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    );
  }

  const RANK_ICON: Record<number, string> = { 1: "👑", 2: "🥈", 3: "🥉" };
  const RANK_LABEL: Record<number, string> = { 1: "1등주", 2: "2등주", 3: "3등주" };

  function SectorLeaderTable({ leaders, onRowClick }: { leaders: SectorLeaderStock[]; onRowClick: (code: string) => void }) {
    return (
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th className="px-4 py-3 text-left w-56">종목명</th>
              <th className="px-4 py-3 text-right">현재가</th>
              <th className="px-4 py-3 text-right">등락률</th>
              <th className="px-4 py-3 text-right">거래대금(억)</th>
              <th className="px-4 py-3 text-right">시총(억)</th>
              <th className="px-4 py-3 text-right">점수</th>
              <th className="px-4 py-3 text-left">점수 구성</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {leaders.map((s) => (
              <tr
                key={s.stock_code}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => onRowClick(s.stock_code)}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    <span className="text-base">{RANK_ICON[s.rank]}</span>
                    <span className="font-medium">{s.stock_name}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      s.rank === 1 ? "bg-amber-100 text-amber-700" :
                      s.rank === 2 ? "bg-slate-100 text-slate-600" :
                      "bg-orange-50 text-orange-600"
                    }`}>{RANK_LABEL[s.rank]}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-400 mt-0.5">
                    <span>{s.stock_code}</span>
                    {s.market && (
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                        s.market === "KOSPI" ? "bg-blue-50 text-blue-600" : "bg-emerald-50 text-emerald-600"
                      }`}>{s.market}</span>
                    )}
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                      s.ma_aligned ? "bg-teal-50 text-teal-600" : "bg-gray-100 text-gray-400"
                    }`}>{s.ma_aligned ? "정배열" : "비정배열"}</span>
                    {(s.tags ?? []).filter((t) => t !== "정배열").map((tag) => (
                      <span key={tag} className="bg-blue-50 text-blue-700 text-[10px] font-semibold px-1.5 py-0.5 rounded">{tag}</span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-mono">{s.current_price > 0 ? s.current_price.toLocaleString() : "-"}</td>
                <td className={`px-4 py-3 text-right font-mono ${s.change_rate >= 0 ? "text-red-500" : "text-blue-500"}`}>
                  {`${s.change_rate >= 0 ? "+" : ""}${s.change_rate.toFixed(2)}%`}
                </td>
                <td className="px-4 py-3 text-right font-mono text-gray-600">
                  {s.transaction_amount > 0 ? Math.round(s.transaction_amount / 1e8).toLocaleString() : "-"}
                </td>
                <td className="px-4 py-3 text-right font-mono text-gray-600">{s.market_cap > 0 ? s.market_cap.toLocaleString() : "-"}</td>
                <td className="px-4 py-3 text-right">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded font-mono ${
                    s.score >= 75 ? "bg-red-100 text-red-700" :
                    s.score >= 50 ? "bg-orange-100 text-orange-700" :
                    "bg-yellow-100 text-yellow-700"
                  }`}>{s.score}</span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1 flex-wrap text-[10px]">
                    <span className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded" title="거래대금">대금 {s.score_detail.amount}</span>
                    <span className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded" title="상승률">상승 {s.score_detail.rate}</span>
                    <span className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded" title="정배열">MA {s.score_detail.ma_aligned}</span>
                    <span className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded" title="시가총액">시총 {s.score_detail.mktcap}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-baseline justify-between mb-4">
        <h1 className="text-2xl font-bold">주식 종목</h1>
        {dataDate && !isSearchMode && (
          <div className="text-xs text-gray-400 text-right">
            <div>기준일: <span className="font-medium text-gray-600">{dataDate}</span></div>
            {generatedAt && (
              <div>생성: <span className="font-medium text-gray-600">{formatGeneratedAt(generatedAt)}</span></div>
            )}
            {priceUpdatedAt && (
              <div>
                가격 갱신:{" "}
                <span className="font-medium text-green-600">
                  {priceUpdatedAt.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 검색 바 */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="종목명 검색..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-9 pr-9 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {isSearchMode ? (
        /* 검색 결과 */
        <div>
          <p className="text-xs text-gray-400 mb-2">
            &ldquo;{searchQuery}&rdquo; 검색 결과 {searchLoading ? "..." : `${searchResults.length}건`}
          </p>
          {searchLoading ? (
            <div className="text-center py-20 text-gray-400">검색 중...</div>
          ) : searchResults.length === 0 ? (
            <div className="text-center py-20 text-gray-400">검색 결과가 없습니다.</div>
          ) : (
            <div className="border rounded-lg overflow-hidden divide-y">
              {searchResults.map((s) => (
                <div
                  key={s.stock_code}
                  className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 cursor-pointer"
                  onClick={() => router.push(`/stocks/${s.stock_code}`)}
                >
                  <div>
                    <span className="font-medium">{s.stock_name}</span>
                    <span className="ml-2 text-gray-400 text-xs font-mono">{s.stock_code}</span>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    s.market === "KOSPI"
                      ? "bg-blue-50 text-blue-600"
                      : "bg-emerald-50 text-emerald-600"
                  }`}>
                    {s.market}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* 기본 탭 뷰 */
        <>
          <div className="flex items-center gap-2 mb-4">
            <button
              onClick={() => setTab("recommend")}
              className={`px-4 py-2 rounded text-sm font-medium ${tab === "recommend" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}
            >
              오늘의 추천
            </button>
            <button
              onClick={() => setTab("sector")}
              className={`flex items-center gap-1.5 px-4 py-2 rounded text-sm font-medium ${tab === "sector" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}
            >
              <TrendingUp className="w-3.5 h-3.5" />
              섹터 주도주
            </button>
            <button
              onClick={() => setTab("favorites")}
              className={`px-4 py-2 rounded text-sm font-medium ${tab === "favorites" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}
            >
              즐겨찾기 ({favorites.length})
            </button>
            {tab === "recommend" && (
              <button
                onClick={refreshRecommendations}
                disabled={refreshing}
                className="ml-auto flex items-center gap-1.5 px-3 py-2 rounded text-sm font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                title="추천 목록 새로고침"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
                {refreshing ? "조회 중..." : "새로고침"}
              </button>
            )}
          </div>
          {tab === "sector" ? (
            <div>
              <p className="text-xs text-gray-500 mb-3">섹터를 선택하면 캐시된 주도주 데이터를 표시합니다. 매일 09:05 자동 갱신됩니다.</p>
              <div className="flex flex-wrap gap-2 mb-4">
                <button
                  onClick={() => {
                    setSelectedSector("전체");
                    setSectorLeaders([]);
                    setSectorUpdatedAt(null);
                    setAllSectorLeaders([]);
                    setSectorLoading(true);
                    api.getAllSectorLeaders()
                      .then((res) => setAllSectorLeaders(res.data ?? []))
                      .catch(() => setAllSectorLeaders([]))
                      .finally(() => setSectorLoading(false));
                  }}
                  className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-colors ${
                    selectedSector === "전체"
                      ? "bg-indigo-600 text-white border-indigo-600"
                      : "bg-indigo-50 text-indigo-700 border-indigo-200 hover:border-indigo-400"
                  }`}
                >
                  전체
                </button>
                {SECTORS.map((s) => (
                  <button
                    key={s}
                    onClick={() => {
                      setSelectedSector(s);
                      setSectorLeaders([]);
                      setSectorUpdatedAt(null);
                      setAllSectorLeaders([]);
                      setSectorLoading(true);
                      api.getSectorLeader(s)
                        .then((res) => { setSectorLeaders(res.data ?? []); setSectorUpdatedAt(res.updated_at ?? null); })
                        .catch(() => setSectorLeaders([]))
                        .finally(() => setSectorLoading(false));
                    }}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                      selectedSector === s
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-white text-gray-700 border-gray-300 hover:border-blue-400 hover:text-blue-600"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>

              {/* 새로 불러오기 버튼 + updated_at */}
              {selectedSector && !sectorLoading && (
                <div className="flex items-center gap-3 mb-4">
                  <button
                    onClick={() => {
                      if (sectorRefreshing) return;
                      setSectorRefreshing(true);
                      if (selectedSector === "전체") {
                        setSectorLoading(true);
                        setAllSectorLeaders([]);
                        setAllSectorProgress(0);
                        let completed = 0;
                        const results: { sector: string; leaders: SectorLeaderStock[]; updated_at: string | null }[] =
                          SECTORS.map((s) => ({ sector: s, leaders: [], updated_at: null }));
                        Promise.allSettled(
                          SECTORS.map((s, i) =>
                            api.getSectorLeader(s, true)
                              .then((res) => { results[i] = { sector: s, leaders: res.data ?? [], updated_at: res.updated_at ?? null }; })
                              .catch(() => {})
                              .finally(() => { completed++; setAllSectorProgress(completed); })
                          )
                        ).then(() => { setAllSectorLeaders([...results]); setSectorLoading(false); setSectorRefreshing(false); });
                      } else {
                        api.getSectorLeader(selectedSector, true)
                          .then((res) => { setSectorLeaders(res.data ?? []); setSectorUpdatedAt(res.updated_at ?? null); })
                          .catch(() => {})
                          .finally(() => setSectorRefreshing(false));
                      }
                    }}
                    disabled={sectorRefreshing}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3 h-3 ${sectorRefreshing ? "animate-spin" : ""}`} />
                    새로 불러오기
                  </button>
                  {selectedSector !== "전체" && sectorUpdatedAt && (
                    <span className="text-xs text-gray-400">기준: {formatGeneratedAt(sectorUpdatedAt)}</span>
                  )}
                </div>
              )}

              {sectorLoading && (
                <div className="text-center py-16 text-gray-400">
                  <div className="text-2xl mb-2">📊</div>
                  <div className="text-sm">
                    {selectedSector === "전체" && sectorRefreshing
                      ? `갱신 중... ${allSectorProgress} / ${SECTORS.length}`
                      : "데이터를 불러오는 중..."}
                  </div>
                </div>
              )}
              {!sectorLoading && selectedSector === "전체" && allSectorLeaders.length > 0 && (
                <div className="space-y-8">
                  {allSectorLeaders.map(({ sector, leaders, updated_at }) => (
                    <div key={sector}>
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="text-sm font-bold text-gray-700 flex items-center gap-1.5">
                          <TrendingUp className="w-3.5 h-3.5 text-blue-500" />
                          {sector}
                        </h3>
                        {updated_at && (
                          <span className="text-[10px] text-gray-400">{formatGeneratedAt(updated_at)}</span>
                        )}
                      </div>
                      {leaders.length > 0
                        ? <SectorLeaderTable leaders={leaders} onRowClick={(code) => router.push(`/stocks/${code}`)} />
                        : <div className="text-xs text-gray-400 py-4 text-center border rounded-lg">캐시 없음 — 새로 불러오기를 눌러주세요</div>
                      }
                    </div>
                  ))}
                </div>
              )}
              {!sectorLoading && selectedSector !== "전체" && sectorLeaders.length > 0 && (
                <SectorLeaderTable leaders={sectorLeaders} onRowClick={(code) => router.push(`/stocks/${code}`)} />
              )}
              {!sectorLoading && selectedSector !== "전체" && selectedSector && sectorLeaders.length === 0 && (
                <div className="text-center py-12 text-gray-400 text-sm">캐시 없음 — 새로 불러오기를 눌러주세요</div>
              )}
              {!selectedSector && (
                <div className="text-center py-16 text-gray-300">
                  <TrendingUp className="w-10 h-10 mx-auto mb-3 opacity-30" />
                  <div className="text-sm">위에서 섹터를 선택하세요</div>
                </div>
              )}
            </div>
          ) : tab === "favorites" && favoritesLoading ? (
            <div className="text-center py-20 text-gray-400">불러오는 중...</div>
          ) : tab !== "favorites" && loading ? (
            <div className="text-center py-20 text-gray-400">불러오는 중...</div>
          ) : (
            <StockTable
              rows={displayed}
              fromTab={tab === "favorites" ? "favorites" : undefined}
            />
          )}
        </>
      )}
    </div>
  );
}
