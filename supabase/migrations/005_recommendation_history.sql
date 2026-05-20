CREATE TABLE IF NOT EXISTS recommendation_history (
    id          SERIAL PRIMARY KEY,
    period_type VARCHAR(10)  NOT NULL,          -- 'daily' | 'weekly' | 'monthly'
    period_key  VARCHAR(20)  NOT NULL,          -- '2026-05-15' | '2026-W20' | '2026-05'
    stocks      JSONB        NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (period_type, period_key)
);

ALTER TABLE recommendation_history DISABLE ROW LEVEL SECURITY;
