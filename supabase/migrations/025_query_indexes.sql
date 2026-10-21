-- v2.0.0 A3: 실제 쿼리 패턴 대비 부족한 인덱스 보강 (모두 IF NOT EXISTS, 재실행 안전)

-- stock_ohlcv: trade_date 범위만으로 전 종목을 읽는 쿼리(시장 ADR 등)용.
-- 기존 (stock_code, trade_date) 인덱스는 stock_code 없이는 쓸 수 없다.
CREATE INDEX IF NOT EXISTS idx_ohlcv_trade_date ON stock_ohlcv (trade_date);

-- virtual_trades: 계좌별 최신 체결 조회(get_trades)와 당일 손절 재매수 금지 확인.
-- (account_id, traded_at DESC) 한 번으로 정렬까지 처리한다.
CREATE INDEX IF NOT EXISTS idx_virtual_trades_account_traded
  ON virtual_trades (account_id, traded_at DESC);

-- stock_recommendations: 최근 날짜 순 이력 조회(neq date + order date desc).
-- 기존 idx_recommendations_date_score 가 date 선두 컬럼이라 대부분 커버되므로 추가 없음.
