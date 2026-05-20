-- Add tech_score to stock_recommendations for frontend display and ordering
ALTER TABLE stock_recommendations ADD COLUMN IF NOT EXISTS tech_score INTEGER DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_recommendations_date_score ON stock_recommendations(date DESC, tech_score DESC);
