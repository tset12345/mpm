from datetime import date, timedelta

import pytest

from app.services import recommendations as rec_mod
from app.services.db_utils import fetch_all
from tests.fakes import FakeSupabase


def seed_ohlcv(db, codes, days, start=date(2026, 1, 1)):
    rows = []
    for d in range(days):
        day = (start + timedelta(days=d)).isoformat()
        for i, code in enumerate(codes):
            rows.append({"stock_code": code, "trade_date": day, "close_price": 100 + d + i,
                         "high_price": 101, "low_price": 99, "open_price": 100, "volume": 10})
    db.seed("stock_ohlcv", rows)
    return rows


def test_unpaginated_query_is_capped_at_1000_rows():
    db = FakeSupabase()
    seed_ohlcv(db, ["A", "B"], 700)
    data = db.table("stock_ohlcv").select("*").order("trade_date").execute().data
    assert len(data) == 1000


def test_fetch_all_returns_every_row_without_duplicates():
    db = FakeSupabase()
    rows = seed_ohlcv(db, ["A", "B", "C"], 700)
    got = fetch_all(lambda: db.table("stock_ohlcv").select("*").order("trade_date").order("stock_code"))
    assert len(got) == len(rows) == 2100
    assert len({(r["stock_code"], r["trade_date"]) for r in got}) == 2100


def test_fetch_all_exact_page_multiple_and_empty():
    db = FakeSupabase()
    seed_ohlcv(db, ["A"], 1000)
    assert len(fetch_all(lambda: db.table("stock_ohlcv").select("*").order("trade_date"))) == 1000
    assert fetch_all(lambda: db.table("nothing").select("*")) == []


def test_fetch_all_respects_filters():
    db = FakeSupabase()
    seed_ohlcv(db, ["A", "B"], 800)
    got = fetch_all(lambda: db.table("stock_ohlcv").select("*").eq("stock_code", "B").order("trade_date"))
    assert len(got) == 800 and {r["stock_code"] for r in got} == {"B"}


def test_load_cached_ohlcv_gets_recent_rows_beyond_cap(monkeypatch):
    import asyncio
    db = FakeSupabase()
    codes = [f"{i:06d}" for i in range(20)]
    seed_ohlcv(db, codes, 120)  # 2,400행 > 1,000
    monkeypatch.setattr(rec_mod, "supabase", db)
    result = asyncio.run(rec_mod._load_cached_ohlcv(codes, "2026-01-01"))
    assert all(len(result[c]) == 120 for c in codes)
    assert result[codes[0]][-1]["trade_date"] == (date(2026, 1, 1) + timedelta(days=119)).isoformat()


def test_adr_uses_all_dates_beyond_cap(monkeypatch):
    from app.routers import market
    db = FakeSupabase()
    days = 40
    today = date.today()
    start = today - timedelta(days=days - 1)
    codes = [f"{i:06d}" for i in range(30)]  # 40일 x 30종목 = 1,200행 > 1,000
    seed_ohlcv(db, codes, days, start=start)
    monkeypatch.setattr(market, "supabase", db)
    out = market.get_adr(days=60)
    dates = [p["date"] for p in out["data"]]
    assert out["status"] == "success"
    assert len(dates) == days - 1
    assert dates[-1] == today.isoformat()
