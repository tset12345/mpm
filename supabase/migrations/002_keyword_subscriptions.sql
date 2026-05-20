CREATE TABLE IF NOT EXISTS keyword_subscriptions (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(100) NOT NULL UNIQUE,
    stock_code VARCHAR(6),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE keyword_subscriptions DISABLE ROW LEVEL SECURITY;
