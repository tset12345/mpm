export interface StockSummary {
  stock_code: string;
  stock_name: string;
  current_price: number | null;
  change_rate: number | null;
  volume: number | null;
  tags: string[];
  tech_score?: number;
  total_score?: number;
  date?: string;
  consecutive_days?: number;
  entry_price?: number | null;
  first_entry_price?: number | null;
  source_conditions?: string[];
  market?: "KOSPI" | "KOSDAQ";
  engine_a_score?: number;
  engine_b_score?: number;
}

export interface TechnicalSignals {
  ma5: number | null;
  ma20: number | null;
  ma60: number | null;
  macd: number | null;
  macd_signal: number | null;
  rsi: number | null;
  stoch_k: number | null;
  stoch_d: number | null;
  bb_upper: number | null;
  bb_lower: number | null;
  bb_bandwidth: number | null;
  disparity: number | null;
  adx: number | null;
  plus_di: number | null;
  minus_di: number | null;
  cci: number | null;
  mfi: number | null;
  atr: number | null;
  obv: number | null;
  volume_ma20: number | null;
  volume_ratio: number | null;
  vr: number | null;
  chaikin_osc: number | null;
  parabolic_sar: number | null;
  env_upper: number | null;
  env_lower: number | null;
  pivot_s2: number | null;
  fib_level: number | null;
  fib_ratio: number | null;
  fib_reason: string | null;
}

export interface PriceInfo {
  ref_price: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  upper_limit: number | null;
  lower_limit: number | null;
  w52_high: number | null;
  w52_low: number | null;
  market_cap: number | null;
  trade_amount: number | null;
  foreign_rate: number | null;
  eps: number | null;
  bps: number | null;
}

export interface ExpectedReturn {
  current_price: number;
  target_per: number;
  sector_name: string | null;
  sector_per: number;
  coe: number;
  target_price_per: number | null;
  target_price_pbr: number | null;
  target_price: number | null;
  target_upside: number | null;
  stop_loss: number;
  stop_loss_rate: number;
  expected_value: number | null;
  risk_reward: number | null;
  verdict: "진입 승인" | "진입 보류" | null;
  verdict_reason: string | null;
}

export interface StockDetail {
  stock_code: string;
  stock_name: string;
  market?: "KOSPI" | "KOSDAQ" | null;
  fetched_at: string;
  current_price: number | null;
  change_rate: number | null;
  change_amount: number | null;
  volume: number | null;
  price_info: PriceInfo;
  metrics: {
    per: number | null;
    pbr: number | null;
    roe: number | null;
  };
  expected_return: ExpectedReturn | null;
  ichimoku: {
    conversion_line: number;
    base_line: number;
    span_a: number;
    span_b: number;
    position: string;
  };
  technical: {
    score: number;
    tags: string[];
    signals: TechnicalSignals;
    score_detail: { engine_a: number; engine_b: number };
    strength: string;
    engine?: "A" | "B" | null;
    engine_a_score?: number;
    engine_b_score?: number;
  };
}


export interface Profile {
  id: number;
  name: string;
  analysis_type: "quant" | "dividend";
  created_at: string;
}

export interface Holding {
  id: number;
  stock_code: string;
  stock_name: string;
  avg_price: number;
  quantity: number;
  memo: string | null;
  created_at: string;
  profile_id: number | null;
  // enriched by backend
  market?: "KOSPI" | "KOSDAQ" | null;
  current_price: number | null;
  change_rate: number | null;
  sector_name: string | null;
  stock_type: string | null;
  price_updated_at: string | null;
  purchase_amount: number;
  eval_amount: number | null;
  profit_loss: number | null;
  profit_rate: number | null;
}

export interface SellSignal {
  category: string;
  name: string;
  description: string;
  pts: number;
}

export interface SellLevels {
  stop_loss_5: number;
  stop_loss_10: number;
  stop_loss_15: number;
  trailing_high_ref?: number;
  trailing_stop_7?: number;
  trailing_stop_10?: number;
  target_per15?: number;
  target_per20?: number;
  target_per25?: number;
  w52_high?: number;
}

export interface SellAnalysis {
  sell_score: number;
  grade: "관망" | "주의" | "매도 검토" | "즉시 매도";
  signals: SellSignal[];
  sell_levels: SellLevels;
  portfolio_weight: number | null;
  current_price: number | null;
}

export interface HoldingSummary {
  total_purchase: number;
  total_eval: number | null;
  total_profit_loss: number | null;
  total_profit_rate: number | null;
}

export interface HistoryEntry {
  period_key: string;
  stocks: StockSummary[];
  created_at: string;
}

export interface PortfolioAnalysis {
  analysis_text: string;
  updated_at: string | null;
}

export interface QuantFactorScore {
  score: number;
  max: number;
  ma20?: number;
  ma20_deviation?: number;
  rsi14?: number | null;
  ma20_pts?: number;
  rsi_pts?: number;
  per?: number | null;
  pbr?: number | null;
  per_pts?: number;
  pbr_pts?: number;
  annualized_vol?: number | null;
  vol_pts?: number;
}

export interface StabilityDetailItem {
  name: string;
  score: number;
  reason: string;
}

export interface StrategyAnalysisData {
  stock_code: string;
  stock_name: string;
  strategy_type: "quant" | "dividend";
  analyzed_at: string;
  current_price: number;
  per: number | null;
  pbr: number | null;
  roe: number | null;
  sector_name: string | null;
  sector_per: number | null;
  verdict: string;
  verdict_reason: string;
  // quant
  quant_score?: number;
  direction_hint?: string;
  factor_scores?: {
    momentum: QuantFactorScore;
    value: QuantFactorScore;
    volatility: QuantFactorScore;
  };
  // dividend
  d0?: number | null;
  d1?: number | null;
  dividend_growth_rate?: number | null;
  dividend_yield?: number | null;
  ggm_expected_return?: number | null;
  stability_score?: number;
  stability_grade?: "안정" | "모니터링" | "위험";
  stability_detail?: StabilityDetailItem[];
}

export interface StockMaster {
  stock_code: string;
  stock_name: string;
  market: "KOSPI" | "KOSDAQ";
}

export interface VirtualAccount {
  id: number;
  profile_id: number | null;
  name: string;
  initial_cash: number;
  current_cash: number;
  strategy: "engine_a" | "engine_b" | "both";
  min_score: number;
  max_positions: number;
  position_size: number;
  stop_loss_pct: number;
  take_profit_pct: number;
  is_active: boolean;
  created_at: string;
}

export interface VirtualPosition {
  id: number;
  account_id: number;
  stock_code: string;
  stock_name: string;
  quantity: number;
  avg_price: number;
  entry_date: string;
  entry_score: number | null;
  engine: "A" | "B" | null;
  current_price: number | null;
  profit_loss: number | null;
  profit_rate: number | null;
  hold_days: number | null;
}

export interface VirtualTrade {
  id: number;
  account_id: number;
  stock_code: string;
  stock_name: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  amount: number;
  trigger_type: "algo_buy" | "stop_loss" | "take_profit" | "sell_signal" | "manual";
  engine: "A" | "B" | null;
  tech_score: number | null;
  sell_score: number | null;
  pnl: number | null;
  pnl_rate: number | null;
  memo: string | null;
  traded_at: string;
  created_at: string;
}

export interface VirtualPerformance {
  initial_cash: number;
  current_cash: number;
  position_value: number;
  total_value: number;
  total_return_rate: number;
  realized_pnl: number;
  unrealized_pnl: number;
  win_rate: number | null;
  trade_count: number;
  sell_count: number;
  avg_hold_days: number | null;
  max_drawdown: number | null;
}

export interface SectorLeaderStock {
  rank: number;
  stock_code: string;
  stock_name: string;
  market?: "KOSPI" | "KOSDAQ" | null;
  current_price: number;
  change_rate: number;
  volume: number;
  market_cap: number;
  transaction_amount: number;
  score: number;
  score_detail: {
    amount: number;
    rate: number;
    ma_aligned: number;
    mktcap: number;
  };
  tags: string[];
  ma5: number | null;
  ma20: number | null;
  ma60: number | null;
  ma_aligned: boolean;
}

// ── Market types ──────────────────────────────────────────────────────────────

export interface MarketStock {
  stock_code: string;
  stock_name: string;
  sector: string;
  current_price: number;
  change_rate: number;
  market_cap: number;
  frgn_ntby_qty: number;
  org_ntby_qty: number;
  volume: number;
  transaction_amount: number;
}

export interface IndexCandle {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  frgn_ntby: number;
}

export interface AdrPoint {
  date: string;
  advancing: number;
  declining: number;
  adr: number;
}

export interface InvestorTrend {
  foreign_net_buy: number;
  institution_net_buy: number;
  individual_net_buy: number;
  stocks: { stock_code: string; stock_name: string; change_rate: number; frgn_ntby_qty: number; org_ntby_qty: number }[];
}

export interface MarketIndexItem {
  label: string;
  price: number | null;
  change: number | null;
  change_rate: number | null;
  sign: string; // "1":상한 "2":상승 "3":보합 "4":하락 "5":하한
}

export interface MarketIndices {
  kospi: MarketIndexItem;
  kosdaq: MarketIndexItem;
  nasdaq: MarketIndexItem;
  usd_krw: MarketIndexItem;
}

export interface SparklinePoint {
  date: string;
  close: number;
}

