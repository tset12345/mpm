-- Add source_conditions: which screening conditions selected this stock
ALTER TABLE stock_recommendations
    ADD COLUMN IF NOT EXISTS source_conditions TEXT[] DEFAULT '{}';
