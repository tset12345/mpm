-- 가상 거래 계좌
CREATE TABLE IF NOT EXISTS virtual_accounts (
    id              serial PRIMARY KEY,
    profile_id      integer REFERENCES profiles(id) ON DELETE CASCADE,
    name            text NOT NULL DEFAULT '가상 계좌',
    initial_cash    integer NOT NULL DEFAULT 10000000,
    current_cash    integer NOT NULL DEFAULT 10000000,
    strategy        text NOT NULL DEFAULT 'both'
                    CHECK (strategy IN ('engine_a', 'engine_b', 'both')),
    min_score       integer NOT NULL DEFAULT 50,
    max_positions   integer NOT NULL DEFAULT 5,
    position_size   integer NOT NULL DEFAULT 20,   -- 종목당 투자 비율(%)
    stop_loss_pct   integer NOT NULL DEFAULT 10,
    take_profit_pct integer NOT NULL DEFAULT 20,
    is_active       boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- 가상 보유 포지션
CREATE TABLE IF NOT EXISTS virtual_positions (
    id           serial PRIMARY KEY,
    account_id   integer NOT NULL REFERENCES virtual_accounts(id) ON DELETE CASCADE,
    stock_code   text NOT NULL,
    stock_name   text NOT NULL,
    quantity     integer NOT NULL,
    avg_price    integer NOT NULL,
    entry_date   date NOT NULL,
    entry_score  integer,
    engine       text CHECK (engine IN ('A', 'B')),
    created_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (account_id, stock_code)
);

-- 가상 체결 내역
CREATE TABLE IF NOT EXISTS virtual_trades (
    id           serial PRIMARY KEY,
    account_id   integer NOT NULL REFERENCES virtual_accounts(id) ON DELETE CASCADE,
    stock_code   text NOT NULL,
    stock_name   text NOT NULL,
    side         text NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity     integer NOT NULL,
    price        integer NOT NULL,
    amount       integer NOT NULL,           -- 체결금액 (price × quantity)
    trigger_type text NOT NULL
                 CHECK (trigger_type IN ('algo_buy', 'stop_loss', 'take_profit', 'sell_signal', 'manual')),
    engine       text CHECK (engine IN ('A', 'B')),
    tech_score   integer,
    sell_score   integer,
    pnl          integer,                    -- 매도 시 실현손익 (매수 시 NULL)
    pnl_rate     numeric(7,2),
    memo         text,
    traded_at    date NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_virtual_positions_account ON virtual_positions(account_id);
CREATE INDEX IF NOT EXISTS idx_virtual_trades_account    ON virtual_trades(account_id);
CREATE INDEX IF NOT EXISTS idx_virtual_trades_traded_at  ON virtual_trades(traded_at DESC);
