import { supabase } from "./supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  const authHeader: Record<string, string> = session
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...authHeader, ...(options?.headers as Record<string, string> | undefined) },
  });
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  getRecommendations: () =>
    fetchAPI<{ status: string; data: import("./types").StockSummary[]; date: string | null; generated_at: string | null }>("/api/v1/stocks/recommend"),

  getRecommendationPrices: () =>
    fetchAPI<{ status: string; data: { stock_code: string; current_price: number | null; change_rate: number | null }[] }>("/api/v1/stocks/recommend/prices"),

  getStockDetail: (code: string) =>
    fetchAPI<{ status: string; data: import("./types").StockDetail }>(`/api/v1/stocks/${code}/detail`),

  searchStocks: (q: string) =>
    fetchAPI<{ status: string; data: import("./types").StockMaster[] }>(`/api/v1/stocks/search?q=${encodeURIComponent(q)}`),

  getHistory: (type: "daily" | "weekly" | "monthly") =>
    fetchAPI<{ status: string; period_type: string; data: import("./types").HistoryEntry[] }>(`/api/v1/stocks/history?type=${type}`),

  getHoldings: (profile_id?: number | null) =>
    fetchAPI<{ status: string; data: import("./types").Holding[]; summary: import("./types").HoldingSummary; price_fetched_at: string | null }>(
      profile_id != null ? `/api/v1/holdings?profile_id=${profile_id}` : "/api/v1/holdings"
    ),

  addHolding: (body: { stock_code: string; stock_name: string; avg_price: number; quantity: number; memo?: string; profile_id?: number | null }) =>
    fetchAPI<{ status: string; data: import("./types").Holding }>("/api/v1/holdings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  getProfiles: () =>
    fetchAPI<{ status: string; data: import("./types").Profile[] }>("/api/v1/profiles"),

  createProfile: (name: string, analysis_type: "quant" | "dividend" = "quant") =>
    fetchAPI<{ status: string; data: import("./types").Profile }>("/api/v1/profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, analysis_type }),
    }),

  updateProfile: (id: number, body: { name?: string; analysis_type?: "quant" | "dividend" }) =>
    fetchAPI<{ status: string; data: import("./types").Profile }>(`/api/v1/profiles/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  deleteProfile: (id: number) =>
    fetchAPI<{ status: string }>(`/api/v1/profiles/${id}`, { method: "DELETE" }),

  updateHolding: (id: number, body: { avg_price?: number; quantity?: number; memo?: string; profile_id?: number | null }) =>
    fetchAPI<{ status: string; data: import("./types").Holding }>(`/api/v1/holdings/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  deleteHolding: (id: number) =>
    fetchAPI<{ status: string }>(`/api/v1/holdings/${id}`, { method: "DELETE" }),

  getSellAnalysis: (id: number) =>
    fetchAPI<{ status: string; data: import("./types").SellAnalysis }>(`/api/v1/holdings/${id}/sell-analysis`),

  getPortfolioAnalysis: (profile_id?: number | null, holdings_hash?: string) => {
    const params = new URLSearchParams();
    if (profile_id != null) params.set("profile_id", String(profile_id));
    if (holdings_hash) params.set("holdings_hash", holdings_hash);
    const qs = params.toString();
    return fetchAPI<{ status: string; data: import("./types").PortfolioAnalysis | null; is_stale: boolean }>(
      `/api/v1/portfolio/analysis${qs ? `?${qs}` : ""}`
    );
  },

  requestPortfolioAnalysis: (profile_id?: number | null) =>
    fetchAPI<{ status: string; data: import("./types").PortfolioAnalysis; is_stale: boolean }>(
      "/api/v1/portfolio/analysis",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: profile_id ?? null }),
      }
    ),

  getStrategyAnalysis: (code: string, strategyType: "quant" | "dividend") =>
    fetchAPI<{ status: string; strategy_type: string; data: import("./types").StrategyAnalysisData; dart_warning?: string }>(
      `/api/v1/analysis/${code}?strategy_type=${strategyType}`
    ),

  getSectorLeader: (sector: string, force = false) =>
    fetchAPI<{ status: string; sector: string; data: import("./types").SectorLeaderStock[]; updated_at: string | null }>(
      `/api/v1/stocks/sector-leader?sector=${encodeURIComponent(sector)}${force ? "&force=true" : ""}`
    ),

  getAllSectorLeaders: () =>
    fetchAPI<{ status: string; data: { sector: string; leaders: import("./types").SectorLeaderStock[]; updated_at: string | null }[] }>(
      "/api/v1/stocks/sector-leader/all"
    ),

  refreshAllSectorLeaders: () =>
    fetchAPI<{ status: string; message: string }>("/api/v1/stocks/sector-leader/refresh", { method: "POST" }),

  getFavorites: () =>
    fetchAPI<{ status: string; data: { stock_code: string; stock_name: string }[] }>("/api/v1/stocks/favorites"),

  addFavorite: (stock_code: string, stock_name: string) =>
    fetchAPI<{ status: string }>("/api/v1/stocks/favorites", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stock_code, stock_name }),
    }),

  removeFavorite: (stock_code: string) =>
    fetchAPI<{ status: string }>(`/api/v1/stocks/favorites/${stock_code}`, { method: "DELETE" }),

  // 가상 거래
  getVirtualAccounts: (profile_id?: number | null) =>
    fetchAPI<{ status: string; data: import("./types").VirtualAccount[] }>(
      profile_id != null ? `/api/v1/virtual/accounts?profile_id=${profile_id}` : "/api/v1/virtual/accounts"
    ),

  createVirtualAccount: (body: {
    name?: string; initial_cash?: number; strategy?: string;
    min_score?: number; max_positions?: number; position_size?: number;
    stop_loss_pct?: number; take_profit_pct?: number; profile_id?: number | null;
  }) =>
    fetchAPI<{ status: string; data: import("./types").VirtualAccount }>("/api/v1/virtual/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  updateVirtualAccount: (id: number, body: Partial<import("./types").VirtualAccount>) =>
    fetchAPI<{ status: string; data: import("./types").VirtualAccount }>(`/api/v1/virtual/accounts/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  deleteVirtualAccount: (id: number) =>
    fetchAPI<{ status: string }>(`/api/v1/virtual/accounts/${id}`, { method: "DELETE" }),

  getVirtualPositions: (account_id: number) =>
    fetchAPI<{ status: string; data: import("./types").VirtualPosition[] }>(`/api/v1/virtual/accounts/${account_id}/positions`),

  getVirtualTrades: (account_id: number) =>
    fetchAPI<{ status: string; data: import("./types").VirtualTrade[] }>(`/api/v1/virtual/accounts/${account_id}/trades`),

  getVirtualPerformance: (account_id: number) =>
    fetchAPI<{ status: string; data: import("./types").VirtualPerformance }>(`/api/v1/virtual/accounts/${account_id}/performance`),

  manualVirtualTrade: (account_id: number, body: {
    side: "buy" | "sell"; stock_code: string; stock_name: string; price: number; quantity?: number;
  }) =>
    fetchAPI<{ status: string; data: unknown }>(`/api/v1/virtual/accounts/${account_id}/trades`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};
