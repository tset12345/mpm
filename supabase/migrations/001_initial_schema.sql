-- Stock recommendations cache (refreshed daily)
CREATE TABLE IF NOT EXISTS stock_recommendations (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    current_price INTEGER NOT NULL,
    change_rate DECIMAL(6,2) NOT NULL,
    volume BIGINT NOT NULL,
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    date DATE DEFAULT CURRENT_DATE,
    UNIQUE(stock_code, date)
);

-- Daily OHLCV cache (keeps last 2 years)
CREATE TABLE IF NOT EXISTS stock_ohlcv (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(6) NOT NULL,
    trade_date DATE NOT NULL,
    open_price INTEGER,
    high_price INTEGER,
    low_price INTEGER,
    close_price INTEGER,
    volume BIGINT,
    UNIQUE(stock_code, trade_date)
);

-- Reports and AI summaries
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    publisher VARCHAR(200),
    publish_date DATE,
    target_stock_code VARCHAR(6),
    raw_text TEXT,
    ai_summary JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ohlcv_stock_date ON stock_ohlcv(stock_code, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_reports_stock ON reports(target_stock_code);
CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(publish_date DESC);
CREATE INDEX IF NOT EXISTS idx_reports_hash ON reports(file_hash);

-- Auto-delete old OHLCV data (keep 2 years)
CREATE OR REPLACE FUNCTION delete_old_ohlcv() RETURNS void AS $$
BEGIN
    DELETE FROM stock_ohlcv WHERE trade_date < CURRENT_DATE - INTERVAL '2 years';
END;
$$ LANGUAGE plpgsql;

-- Disable RLS for backend service_role access
ALTER TABLE stock_recommendations DISABLE ROW LEVEL SECURITY;
ALTER TABLE stock_ohlcv DISABLE ROW LEVEL SECURITY;
ALTER TABLE reports DISABLE ROW LEVEL SECURITY;
