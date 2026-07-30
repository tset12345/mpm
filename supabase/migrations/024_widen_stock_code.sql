-- 일부 KIS API가 6자 초과 종목코드를 반환하는 경우 저장 실패 방지
-- stock_recommendations, stock_ohlcv, 관련 테이블 모두 VARCHAR(12)로 확장
ALTER TABLE stock_recommendations ALTER COLUMN stock_code TYPE VARCHAR(12);
ALTER TABLE stock_ohlcv           ALTER COLUMN stock_code TYPE VARCHAR(12);
ALTER TABLE reports               ALTER COLUMN target_stock_code TYPE VARCHAR(12);
