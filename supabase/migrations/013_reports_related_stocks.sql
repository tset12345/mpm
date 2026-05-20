-- Add related_stock_codes column to reports table
ALTER TABLE reports ADD COLUMN IF NOT EXISTS related_stock_codes JSONB DEFAULT '[]';
