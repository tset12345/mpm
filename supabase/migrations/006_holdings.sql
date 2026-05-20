CREATE TABLE IF NOT EXISTS holdings (
  id           SERIAL PRIMARY KEY,
  stock_code   VARCHAR(10)   NOT NULL,
  stock_name   VARCHAR(100)  NOT NULL,
  avg_price    INTEGER       NOT NULL CHECK (avg_price > 0),
  quantity     INTEGER       NOT NULL CHECK (quantity > 0),
  memo         TEXT,
  created_at   TIMESTAMPTZ   DEFAULT NOW(),
  updated_at   TIMESTAMPTZ   DEFAULT NOW()
);

ALTER TABLE holdings DISABLE ROW LEVEL SECURITY;
