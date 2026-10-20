from datetime import date

import pytest

from app.services import virtual_trading as vt
from tests.fakes import FakeSupabase

TODAY = date(2026, 3, 10)


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(vt, "supabase", fake)
    monkeypatch.setattr(vt, "_today", lambda: TODAY)
    monkeypatch.setattr(vt, "_fire_telegram", lambda coro: coro.close())
    return fake


def make_account(db, **over):
    base = {
        "name": "t", "initial_cash": 10_000_000, "current_cash": 10_000_000,
        "strategy": "both", "min_score": 50, "max_score": None, "score_filter_type": "gte",
        "max_positions": 5, "position_size": 20, "stop_loss_pct": 10, "take_profit_pct": 20,
        "is_active": True, "max_hold_days": None,
    }
    base.update(over)
    return dict(db.seed("virtual_accounts", [base])[0])


def make_position(db, account, code="005930", **over):
    base = {
        "account_id": account["id"], "stock_code": code, "stock_name": "삼성전자",
        "quantity": 10, "avg_price": 50_000, "entry_date": TODAY.isoformat(),
        "engine": None, "entry_atr": None, "highest_price": 50_000,
        "half_exited": False, "entry_low": None,
    }
    base.update(over)
    return dict(db.seed("virtual_positions", [base])[0])


def seed_flat_ohlcv(db, code, n=20, price=50_000, spread=100):
    rows = [
        {"stock_code": code, "trade_date": f"2026-02-{i + 1:02d}", "close_price": price,
         "high_price": price + spread, "low_price": price - spread, "volume": 100_000}
        for i in range(n)
    ]
    db.seed("stock_ohlcv", rows)


def seed_oscillating_ohlcv(db, code, n=20, low=49_900, high=50_100):
    """RSI가 중립(약 50)에 머무르도록 번갈아 오르내리는 시세."""
    rows = [
        {"stock_code": code, "trade_date": f"2026-02-{i + 1:02d}",
         "close_price": high if i % 2 else low,
         "high_price": high + 50, "low_price": low - 50, "volume": 100_000}
        for i in range(n)
    ]
    db.seed("stock_ohlcv", rows)


def rec(code, score=60, price=10_000, **over):
    base = {"stock_code": code, "stock_name": code, "tech_score": score, "current_price": price,
            "tags": [], "engine_a_score": 0, "engine_b_score": 0}
    base.update(over)
    return base


def trades(db, side=None):
    rows = db.tables.get("virtual_trades", [])
    return [r for r in rows if side is None or r["side"] == side]


def cash(db, account):
    return db.tables["virtual_accounts"][0]["current_cash"] if account else None


# ── 체결 ──────────────────────────────────────────────────────────────────────

def test_execute_buy_sizes_position_and_updates_cash(db):
    acc = make_account(db)
    result = vt._execute_buy(acc, "005930", "삼성전자", 50_000, "algo_buy", "A", 70)
    assert result == {"stock_code": "005930", "quantity": 40, "price": 50_000, "amount": 2_000_000}
    pos = db.tables["virtual_positions"][0]
    assert pos["quantity"] == 40 and pos["avg_price"] == 50_000 and pos["highest_price"] == 50_000
    assert cash(db, acc) == 8_000_000
    assert trades(db, "buy")[0]["trigger_type"] == "algo_buy"


def test_execute_buy_skips_when_quantity_zero(db):
    acc = make_account(db, current_cash=100_000)
    assert vt._execute_buy(acc, "005930", "x", 50_000, "algo_buy", None, None) is None
    assert "virtual_trades" not in db.tables or not db.tables["virtual_trades"]
    assert cash(db, acc) == 100_000


def test_execute_buy_records_entry_atr_and_low_from_history(db):
    acc = make_account(db)
    seed_flat_ohlcv(db, "005930", n=20, price=50_000, spread=100)
    vt._execute_buy(acc, "005930", "x", 50_000, "algo_buy", "A", 70)
    pos = db.tables["virtual_positions"][0]
    assert pos["entry_atr"] == 200
    assert pos["entry_low"] == 49_900


def test_execute_sell_full_closes_position_and_credits_cash(db):
    acc = make_account(db, current_cash=1_000_000)
    pos = make_position(db, acc, quantity=10, avg_price=50_000)
    result = vt._execute_sell(acc, pos, 55_000, "take_profit", None)
    assert result["pnl"] == 50_000
    assert db.tables["virtual_positions"] == []
    assert cash(db, acc) == 1_550_000
    sell = trades(db, "sell")[0]
    assert sell["pnl"] == 50_000 and sell["pnl_rate"] == 10.0


def test_execute_sell_partial_sets_half_exited(db):
    acc = make_account(db, current_cash=0)
    pos = make_position(db, acc, quantity=10)
    vt._execute_sell(acc, pos, 51_000, "ma20_half_exit", None, quantity=5)
    remaining = db.tables["virtual_positions"][0]
    assert remaining["quantity"] == 5 and remaining["half_exited"] is True
    assert cash(db, acc) == 255_000


def test_execute_sell_zero_quantity_is_noop(db):
    acc = make_account(db)
    pos = make_position(db, acc)
    assert vt._execute_sell(acc, pos, 50_000, "manual", None, quantity=0) is None
    assert not trades(db)


# ── 자동 매수 ─────────────────────────────────────────────────────────────────

def test_buy_respects_min_score(db):
    acc = make_account(db, min_score=50)
    vt._process_buy_for_account(acc, [rec("A1", 40), rec("B1", 60)])
    assert [t["stock_code"] for t in trades(db, "buy")] == ["B1"]


def test_buy_respects_max_positions(db):
    acc = make_account(db, max_positions=2)
    vt._process_buy_for_account(acc, [rec("A1"), rec("B1"), rec("C1")])
    assert len(trades(db, "buy")) == 2


def test_buy_skips_held_and_same_day_stop_loss(db):
    acc = make_account(db)
    make_position(db, acc, code="HELD")
    db.seed("virtual_trades", [{
        "account_id": acc["id"], "stock_code": "STOPPED", "side": "sell",
        "trigger_type": "stop_loss", "traded_at": TODAY.isoformat(),
    }])
    vt._process_buy_for_account(acc, [rec("HELD"), rec("STOPPED"), rec("NEW")])
    assert [t["stock_code"] for t in trades(db, "buy")] == ["NEW"]


def test_buy_stop_loss_ban_expires_next_day(db):
    acc = make_account(db)
    db.seed("virtual_trades", [{
        "account_id": acc["id"], "stock_code": "OLD", "side": "sell",
        "trigger_type": "stop_loss", "traded_at": "2026-03-09",
    }])
    vt._process_buy_for_account(acc, [rec("OLD")])
    assert [t["stock_code"] for t in trades(db, "buy")] == ["OLD"]


def test_buy_cash_shrinks_within_loop(db):
    acc = make_account(db, current_cash=1_000_000, position_size=50)
    vt._process_buy_for_account(acc, [rec("A1", price=1_000), rec("B1", price=1_000)])
    qty = [t["quantity"] for t in trades(db, "buy")]
    assert qty == [500, 250]


@pytest.mark.parametrize("strategy,a,b,tags,bought", [
    ("engine_a", 0, 50, [], False),
    ("engine_a", 50, 0, [], True),
    ("engine_b", 50, 0, [], False),
    ("engine_b", 0, 50, [], True),
    ("both_and", 50, 0, [], False),
    ("both_and", 50, 40, [], True),
    ("both", 0, 0, ["추세 돌파형"], True),
    ("both", 0, 0, [], True),
])
def test_buy_strategy_filters(db, strategy, a, b, tags, bought):
    acc = make_account(db, strategy=strategy)
    vt._process_buy_for_account(acc, [rec("X1", engine_a_score=a, engine_b_score=b, tags=tags)])
    assert bool(trades(db, "buy")) is bought


def test_both_and_uses_higher_engine(db):
    acc = make_account(db, strategy="both_and")
    vt._process_buy_for_account(acc, [rec("X1", engine_a_score=30, engine_b_score=60)])
    assert trades(db, "buy")[0]["engine"] == "B"


def test_engine_b_large_cap_filter(db):
    acc = make_account(db, strategy="engine_b", filter_excl_large_cap=True,
                       filter_large_cap_threshold=50_000)
    vt._process_buy_for_account(acc, [
        rec("BIG", engine_b_score=50, market_cap_e8=90_000),
        rec("SMALL", engine_b_score=50, market_cap_e8=3_000),
    ])
    assert [t["stock_code"] for t in trades(db, "buy")] == ["SMALL"]


def test_engine_b_high_amount_filter(db):
    acc = make_account(db, strategy="engine_b", filter_excl_high_amount=True,
                       filter_high_amount_threshold=5_000)
    vt._process_buy_for_account(acc, [
        rec("HOT", engine_b_score=50, daily_amount_e8=9_000),
        rec("CALM", engine_b_score=50, daily_amount_e8=100),
    ])
    assert [t["stock_code"] for t in trades(db, "buy")] == ["CALM"]


def test_buy_skips_invalid_price(db):
    acc = make_account(db)
    vt._process_buy_for_account(acc, [rec("A1", price=0), rec("B1", price=None)])
    assert not trades(db, "buy")


# ── 자동 매도 ─────────────────────────────────────────────────────────────────

def sold(db):
    return [(t["stock_code"], t["trigger_type"]) for t in trades(db, "sell")]


def test_sell_stop_loss(db):
    acc = make_account(db, stop_loss_pct=10)
    make_position(db, acc)
    vt._process_sell_for_account(acc, {"005930": 44_999})
    assert sold(db) == [("005930", "stop_loss")]


def test_sell_not_triggered_just_inside_stop_loss(db):
    acc = make_account(db, stop_loss_pct=10)
    make_position(db, acc)
    vt._process_sell_for_account(acc, {"005930": 45_001})
    assert not sold(db)


def test_sell_take_profit(db):
    acc = make_account(db, take_profit_pct=20)
    make_position(db, acc)
    vt._process_sell_for_account(acc, {"005930": 60_000})
    assert sold(db) == [("005930", "take_profit")]


def test_sell_skips_codes_without_price(db):
    acc = make_account(db)
    make_position(db, acc)
    vt._process_sell_for_account(acc, {})
    assert not sold(db)


def test_sell_max_hold_exit(db):
    acc = make_account(db, max_hold_days=5)
    make_position(db, acc, entry_date="2026-03-04")
    vt._process_sell_for_account(acc, {"005930": 50_500})
    assert sold(db) == [("005930", "max_hold_exit")]


def test_sell_max_hold_not_reached(db):
    acc = make_account(db, max_hold_days=5)
    make_position(db, acc, entry_date="2026-03-06")
    vt._process_sell_for_account(acc, {"005930": 50_500})
    assert not sold(db)


def test_sell_needs_history_for_engine_rules(db):
    acc = make_account(db)
    make_position(db, acc, engine="B", entry_low=60_000)
    seed_flat_ohlcv(db, "005930", n=10)
    vt._process_sell_for_account(acc, {"005930": 49_000})
    assert not sold(db)


def test_engine_a_atr_hard_stop(db):
    acc = make_account(db)
    make_position(db, acc, engine="A", entry_atr=1_000)
    seed_flat_ohlcv(db, "005930")
    vt._process_sell_for_account(acc, {"005930": 48_000})
    assert sold(db) == [("005930", "atr_hard_stop")]


def test_engine_a_updates_highest_price(db):
    acc = make_account(db)
    pos = make_position(db, acc, engine="A", entry_atr=None, highest_price=50_000)
    seed_flat_ohlcv(db, "005930")
    vt._process_sell_for_account(acc, {"005930": 52_000})
    assert db.tables["virtual_positions"][0]["highest_price"] == 52_000
    assert not sold(db)


def test_engine_a_trailing_stop_from_highest(db):
    acc = make_account(db)
    make_position(db, acc, engine="A", entry_atr=None, highest_price=56_000)
    seed_flat_ohlcv(db, "005930", spread=100)
    vt._process_sell_for_account(acc, {"005930": 55_000})
    assert sold(db) == [("005930", "atr_trailing_stop")]


def test_engine_b_entry_low_breach(db):
    acc = make_account(db)
    make_position(db, acc, engine="B", entry_low=49_000)
    seed_flat_ohlcv(db, "005930")
    vt._process_sell_for_account(acc, {"005930": 48_500})
    assert sold(db) == [("005930", "entry_low_breach")]


def test_engine_b_time_limit_stop(db):
    acc = make_account(db)
    make_position(db, acc, engine="B", entry_date="2026-03-04", entry_low=45_000)
    seed_flat_ohlcv(db, "005930")
    vt._process_sell_for_account(acc, {"005930": 49_500})
    assert sold(db) == [("005930", "time_limit_stop")]


def test_engine_b_holds_when_in_profit_after_time_limit(db):
    acc = make_account(db)
    make_position(db, acc, engine="B", entry_date="2026-03-04", entry_low=45_000, half_exited=True)
    seed_oscillating_ohlcv(db, "005930")
    vt._process_sell_for_account(acc, {"005930": 50_100})
    assert not sold(db)


def test_engine_b_target_reached_on_high_rsi(db):
    acc = make_account(db)
    make_position(db, acc, engine="B", entry_low=45_000, half_exited=True)
    seed_flat_ohlcv(db, "005930")
    vt._process_sell_for_account(acc, {"005930": 50_100})
    assert sold(db) == [("005930", "target_reached")]


def test_engine_b_ma20_half_exit(db):
    acc = make_account(db)
    make_position(db, acc, engine="B", quantity=10, entry_low=45_000)
    closes = [50_000] * 18 + [48_000, 48_000]
    db.seed("stock_ohlcv", [
        {"stock_code": "005930", "trade_date": f"2026-02-{i + 1:02d}", "close_price": c,
         "high_price": c + 100, "low_price": c - 100, "volume": 1}
        for i, c in enumerate(closes)
    ])
    vt._process_sell_for_account(acc, {"005930": 50_100})
    assert sold(db) == [("005930", "ma20_half_exit")]
    assert trades(db, "sell")[0]["quantity"] == 5
    assert db.tables["virtual_positions"][0]["half_exited"] is True


def test_sell_trigger_skips_inactive_accounts(db):
    acc = make_account(db, is_active=False)
    make_position(db, acc)
    vt.virtual_sell_trigger({"005930": 1_000})
    assert not sold(db)


def test_sell_trigger_isolates_account_errors(db, monkeypatch):
    a1 = make_account(db)
    a2 = make_account(db)
    make_position(db, a2)
    calls = []

    def fake_process(account, price_map):
        calls.append(account["id"])
        if account["id"] == a1["id"]:
            raise RuntimeError("boom")

    monkeypatch.setattr(vt, "_process_sell_for_account", fake_process)
    vt.virtual_sell_trigger({"005930": 1_000})
    assert calls == [a1["id"], a2["id"]]


# ── 수동 체결 ─────────────────────────────────────────────────────────────────

def test_manual_buy_rejects_insufficient_cash(db):
    acc = make_account(db, current_cash=100_000)
    with pytest.raises(ValueError, match="잔액"):
        vt.manual_trade(acc["id"], "buy", "005930", "x", 50_000, quantity=3)


def test_manual_buy_with_quantity_debits_cash(db):
    acc = make_account(db, current_cash=1_000_000)
    r = vt.manual_trade(acc["id"], "buy", "005930", "x", 50_000, quantity=4)
    assert r["amount"] == 200_000
    assert cash(db, acc) == 800_000


def test_manual_sell_without_position_raises(db):
    acc = make_account(db)
    with pytest.raises(ValueError, match="포지션"):
        vt.manual_trade(acc["id"], "sell", "005930", "x", 50_000)


def test_manual_trade_unknown_account_raises(db):
    with pytest.raises(ValueError, match="계좌"):
        vt.manual_trade(999, "buy", "005930", "x", 50_000)


def test_update_account_ignores_unknown_fields(db):
    acc = make_account(db)
    vt.update_account(acc["id"], {"name": "new", "current_cash": 1})
    row = db.tables["virtual_accounts"][0]
    assert row["name"] == "new" and row["current_cash"] == 10_000_000
