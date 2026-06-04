-- Enable RLS on all tables.
--
-- service_role key (backend) bypasses RLS entirely — no backend changes needed.
-- anon key (Supabase client) gets default-deny on all tables (no policies = no access).
-- This closes direct PostgREST access via the public anon key.

ALTER TABLE stock_recommendations   ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_ohlcv             ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE keyword_subscriptions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendation_history  ENABLE ROW LEVEL SECURITY;
ALTER TABLE holdings                ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles                ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_analyses      ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_master            ENABLE ROW LEVEL SECURITY;
ALTER TABLE sector_leaders          ENABLE ROW LEVEL SECURITY;
ALTER TABLE favorites               ENABLE ROW LEVEL SECURITY;
ALTER TABLE virtual_accounts        ENABLE ROW LEVEL SECURITY;
ALTER TABLE virtual_positions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE virtual_trades          ENABLE ROW LEVEL SECURITY;
