-- Add entry_price (price at first recommendation) and updated_at (last sync time) to stock_recommendations
ALTER TABLE stock_recommendations ADD COLUMN IF NOT EXISTS entry_price  INTEGER;
ALTER TABLE stock_recommendations ADD COLUMN IF NOT EXISTS updated_at   TIMESTAMPTZ DEFAULT NOW();

-- Backfill entry_price = current_price for existing rows that have no entry_price
UPDATE stock_recommendations SET entry_price = current_price WHERE entry_price IS NULL;
