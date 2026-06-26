-- virtual_accounts: Engine B 종목 필터 + 최대 보유일수
ALTER TABLE virtual_accounts
  ADD COLUMN IF NOT EXISTS filter_excl_large_cap      boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS filter_large_cap_threshold integer          DEFAULT 50000,   -- 억원
  ADD COLUMN IF NOT EXISTS filter_excl_high_amount    boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS filter_high_amount_threshold integer        DEFAULT 5000,    -- 억원
  ADD COLUMN IF NOT EXISTS max_hold_days              integer;                          -- NULL = 제한없음

-- stock_recommendations: 시가총액·거래대금 저장 (종목 필터 기준값)
ALTER TABLE stock_recommendations
  ADD COLUMN IF NOT EXISTS market_cap_e8   bigint,   -- 시가총액 (억원)
  ADD COLUMN IF NOT EXISTS daily_amount_e8 bigint;   -- 일 거래대금 (억원)
