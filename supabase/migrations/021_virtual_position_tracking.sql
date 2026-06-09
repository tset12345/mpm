-- virtual_positions 엔진별 청산 로직 지원 컬럼 추가
-- entry_atr    : 매수 시점 ATR (Engine A ATR 스탑 계산용)
-- highest_price: 보유 중 최고가 (Engine A 트레일링 스탑 기준)
-- half_exited  : Engine B MA20 분할 익절 완료 여부
-- entry_low    : 매수 당일 저가 (Engine B 진입 저점 손절 기준)

ALTER TABLE virtual_positions
    ADD COLUMN IF NOT EXISTS entry_atr     INTEGER,
    ADD COLUMN IF NOT EXISTS highest_price INTEGER,
    ADD COLUMN IF NOT EXISTS half_exited   BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS entry_low     INTEGER;
