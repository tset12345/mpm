-- 즐겨찾기 종목 (서버 저장 → 기기/환경 무관하게 동기화)
CREATE TABLE IF NOT EXISTS favorites (
    stock_code  VARCHAR(10)  PRIMARY KEY,
    stock_name  TEXT         NOT NULL,
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

ALTER TABLE favorites DISABLE ROW LEVEL SECURITY;
