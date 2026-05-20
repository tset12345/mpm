CREATE TABLE IF NOT EXISTS stock_master (
    stock_code  VARCHAR(10)  PRIMARY KEY,
    stock_name  TEXT         NOT NULL,
    market      VARCHAR(10)  NOT NULL  -- 'KOSPI' | 'KOSDAQ'
);

CREATE INDEX IF NOT EXISTS idx_stock_master_name ON stock_master (stock_name);

ALTER TABLE stock_master DISABLE ROW LEVEL SECURITY;
