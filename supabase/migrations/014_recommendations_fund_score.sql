-- Add fund_score (AI report score) and total_score (tech + fund) to stock_recommendations
ALTER TABLE stock_recommendations ADD COLUMN IF NOT EXISTS fund_score  INTEGER DEFAULT 0;
ALTER TABLE stock_recommendations ADD COLUMN IF NOT EXISTS total_score INTEGER DEFAULT 0;

-- Index for ordering by total_score
CREATE INDEX IF NOT EXISTS idx_recommendations_date_total ON stock_recommendations(date DESC, total_score DESC);
