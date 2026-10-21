import asyncio
import threading
import time

import pytest

from app.routers import holdings, stocks, virtual
from app.services import market_data, scheduler, virtual_trading as vt
from tests.fakes import FakeSupabase


def run(coro):
    return asyncio.run(coro)


class SlowDB(FakeSupabase):
    """execute()가 동기적으로 지연되는 DB — 이벤트 루프를 막으면 하트비트가 끊긴다."""

    def __init__(self, delay=0.15):
        super().__init__()
        self.delay = delay
        self.threads = set()

    def table(self, name):
        q = super().table(name)
        original = q.execute

        def slow_execute():
            self.threads.add(threading.current_thread())
            time.sleep(self.delay)
            return original()

        q.execute = slow_execute
        return q


async def max_loop_lag(work, interval=0.01):
    """work()가 도는 동안 이벤트 루프가 interval보다 얼마나 늦게 깨어났는지(최대) 측정한다."""
    lag = 0.0
    done = asyncio.Event()

    async def heartbeat():
        nonlocal lag
        while not done.is_set():
            before = time.perf_counter()
            await asyncio.sleep(interval)
            lag = max(lag, time.perf_counter() - before - interval)

    hb = asyncio.create_task(heartbeat())
    try:
        result = await work()
    finally:
        done.set()
        await hb
    return result, lag


def test_event_loop_stays_responsive_during_slow_db(monkeypatch):
    db = SlowDB(delay=0.15)
    db.seed("holdings", [{"stock_code": "005930", "stock_name": "삼성전자", "avg_price": 70000,
                          "quantity": 1, "created_at": "2026-01-01"}])
    monkeypatch.setattr(holdings, "supabase", db)

    async def fake_price(code):
        return {"output": {"stck_prpr": "71000", "prdy_ctrt": "1.0"}}

    monkeypatch.setattr(holdings, "get_price_data", fake_price)

    result, lag = run(max_loop_lag(lambda: holdings.list_holdings(profile_id=None)))
    assert result["status"] == "success" and result["data"][0]["current_price"] == 71000
    assert threading.main_thread() not in db.threads
    assert lag < 0.08, f"이벤트 루프가 {lag:.2f}s 멈췄다"


def test_virtual_positions_endpoint_does_not_block_loop(monkeypatch):
    db = SlowDB(delay=0.1)
    acc = db.seed("virtual_accounts", [{"name": "t"}])[0]
    db.seed("virtual_positions", [{"account_id": acc["id"], "stock_code": "005930", "stock_name": "x",
                                   "quantity": 1, "avg_price": 100, "entry_date": "2026-03-01"}])
    monkeypatch.setattr(virtual, "supabase", db, raising=False)
    monkeypatch.setattr(vt, "supabase", db)

    async def fake_prices(codes):
        return {"005930": 110}

    monkeypatch.setattr(virtual, "_fetch_realtime_prices", fake_prices)
    result, lag = run(max_loop_lag(lambda: virtual.get_positions(acc["id"])))
    assert result["data"][0]["current_price"] == 110
    assert lag < 0.08


def test_telegram_from_worker_thread_reaches_main_loop(monkeypatch):
    received = []

    async def notify():
        received.append(threading.current_thread() is threading.main_thread())

    async def go():
        vt.set_main_loop(asyncio.get_running_loop())
        await asyncio.to_thread(lambda: vt._fire_telegram(notify()))
        await asyncio.sleep(0.05)

    run(go())
    assert received == [True]


def test_telegram_in_loop_thread_creates_task():
    received = []

    async def notify():
        received.append(1)

    async def go():
        vt._fire_telegram(notify())
        await asyncio.sleep(0.01)

    run(go())
    assert received == [1]


def test_telegram_without_any_loop_runs_directly():
    received = []

    async def notify():
        received.append(1)

    vt._main_loop = None
    vt._fire_telegram(notify())
    assert received == [1]


def test_daily_sync_runs_trade_triggers_off_the_event_loop(monkeypatch):
    seen = {}
    stocks_list = [{"stock_code": "005930", "stock_name": "삼성전자", "current_price": 100}]

    async def fake_update():
        return stocks_list

    async def fake_sync_ohlcv(codes):
        return {}

    async def fake_report(stocks):
        return None

    async def fake_prices(codes):
        return {"005930": 101}

    def record(name):
        def fn(*a, **k):
            seen[name] = threading.current_thread() is threading.main_thread()
        return fn

    import app.services.history as history
    import app.services.ohlcv_sync as ohlcv_sync
    import app.services.recommendations as recs
    import app.services.telegram as tg

    monkeypatch.setattr(recs, "update_recommendations", fake_update)
    monkeypatch.setattr(ohlcv_sync, "sync_ohlcv", fake_sync_ohlcv)
    monkeypatch.setattr(history, "save_snapshot", record("snapshot"))
    monkeypatch.setattr(tg, "send_recommendation_report", fake_report)
    monkeypatch.setattr(scheduler, "_fetch_realtime_prices", fake_prices)
    monkeypatch.setattr(scheduler, "_collect_position_codes", lambda: set())
    monkeypatch.setattr(vt, "virtual_sell_trigger", record("sell"))
    monkeypatch.setattr(vt, "virtual_buy_trigger", record("buy"))
    monkeypatch.setattr(scheduler, "_sync_running", False)

    run(scheduler.run_daily_sync())
    assert seen == {"snapshot": False, "sell": False, "buy": False}


# ── 추천 종목 캐시 ────────────────────────────────────────────────────────────

@pytest.fixture
def rec_env(monkeypatch):
    db = SlowDB(delay=0.0)
    db.seed("stock_recommendations", [
        {"stock_code": "A", "stock_name": "A", "date": "2026-10-20", "total_score": 70,
         "tech_score": 70, "current_price": 100, "entry_price": 100, "updated_at": "2026-10-20T09:00"},
        {"stock_code": "B", "stock_name": "B", "date": "2026-10-20", "total_score": 60,
         "tech_score": 60, "current_price": 200, "entry_price": 200, "updated_at": "2026-10-20T09:00"},
    ])
    monkeypatch.setattr(stocks, "supabase", db)
    monkeypatch.setattr(stocks, "_recompute_scores", lambda codes: {})
    stocks._recommend_cache.invalidate()
    stocks._codes_cache.invalidate()
    market_data._price_cache.invalidate()
    calls = {"price": 0}

    async def fake_price(code):
        calls["price"] += 1
        return {"output": {"stck_prpr": "150" if code == "A" else "250", "prdy_ctrt": "2.5"}}

    monkeypatch.setattr(stocks, "get_price_data", fake_price)
    return db, calls


def test_recommend_loads_db_once_for_concurrent_requests(rec_env):
    db, calls = rec_env
    original_table = db.table
    reads = []

    def counting_table(name):
        reads.append(name)
        return original_table(name)

    db.table = counting_table

    async def go():
        return await asyncio.gather(*[stocks.get_recommendations() for _ in range(8)])

    results = run(go())
    assert all(r["status"] == "success" and len(r["data"]) == 2 for r in results)
    assert reads.count("stock_recommendations") == 3  # 최신 날짜·본 조회·과거 이력 — 요청 수와 무관


def test_recommend_overlays_prices_without_mutating_cache(rec_env):
    run(stocks.get_recommendations())
    cached = stocks._recommend_cache.peek("recommend")
    assert [r["current_price"] for r in cached["rows"]] == [100, 200]  # 캐시 원본은 DB 값 유지

    out = run(stocks.get_recommendations())
    prices = {r["stock_code"]: (r["current_price"], r["change_rate"]) for r in out["data"]}
    assert prices == {"A": (150, 2.5), "B": (250, 2.5)}


def test_recommend_prices_endpoint_shares_price_cache(rec_env):
    _, calls = rec_env
    out = run(stocks.get_recommendation_prices())
    assert {d["stock_code"]: d["current_price"] for d in out["data"]} == {"A": 150, "B": 250}
    assert calls["price"] == 2


def test_empty_recommendations_are_not_cached(monkeypatch):
    db = FakeSupabase()
    monkeypatch.setattr(stocks, "supabase", db)
    stocks._recommend_cache.invalidate()
    out = run(stocks.get_recommendations())
    assert out["data"] == [] and out["date"] is None
    assert len(stocks._recommend_cache) == 0


# ── 포지션 현재가 폴백 쿼리 수 ────────────────────────────────────────────────

def test_positions_fallback_uses_one_batch_query(monkeypatch):
    db = FakeSupabase()
    acc = db.seed("virtual_accounts", [{"name": "t"}])[0]
    codes = [f"{i:06d}" for i in range(6)]
    db.seed("virtual_positions", [
        {"account_id": acc["id"], "stock_code": c, "stock_name": c, "quantity": 1,
         "avg_price": 100, "entry_date": "2026-03-01"} for c in codes
    ])
    from datetime import date, timedelta
    today = date.today()
    db.seed("stock_ohlcv", [
        {"stock_code": c, "trade_date": (today - timedelta(days=d)).isoformat(), "close_price": 100 + d}
        for c in codes[:5] for d in range(3)
    ])
    monkeypatch.setattr(vt, "supabase", db)
    monkeypatch.setattr(vt, "_today", lambda: today)

    reads = []
    original = db.table
    db.table = lambda name: (reads.append(name), original(name))[1]

    positions = vt.get_positions(acc["id"], realtime_prices=None)
    by_code = {p["stock_code"]: p["current_price"] for p in positions}
    assert by_code[codes[0]] == 100          # 가장 최근 종가
    assert by_code[codes[5]] is None         # 시세가 전혀 없는 종목
    # 종목 6개: 최신 추천(1) + 가격(1) + 일괄 OHLCV(1) + 시세 없는 1종목 개별 확인(1) + 포지션(1)
    assert reads.count("stock_ohlcv") == 2


@pytest.fixture
def kis_env(rec_env, monkeypatch):
    """get_price_data(캐시 계층)는 그대로 두고 KIS 클라이언트만 가짜로 바꿔 호출 횟수를 센다."""
    monkeypatch.setattr(stocks, "get_price_data", market_data.get_price_data)
    market_data._price_cache.invalidate()
    calls = {"kis": 0}

    async def fake_kis(code):
        calls["kis"] += 1
        await asyncio.sleep(0.01)
        return {"output": {"stck_prpr": "150", "prdy_ctrt": "2.5"}}

    monkeypatch.setattr(market_data.kis_client, "get_stock_price", fake_kis)
    return calls


def test_many_polling_clients_cost_one_kis_call_per_code(kis_env):
    async def go():
        return await asyncio.gather(*[stocks.get_recommendation_prices() for _ in range(50)])

    results = run(go())
    assert all(len(r["data"]) == 2 for r in results)
    assert kis_env["kis"] == 2  # 50명이 동시에 폴링해도 종목 수(2)만큼만 KIS 호출 (이전: 50 x 2 = 100)


def test_rapid_second_poll_within_ttl_makes_no_kis_calls(kis_env):
    run(stocks.get_recommendation_prices())
    run(stocks.get_recommendation_prices())
    assert kis_env["kis"] == 2
