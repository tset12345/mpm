import asyncio

import pytest

from app.routers import market
from tests.fakes import FakeSupabase


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def clean_caches():
    for name in dir(market):
        if name.endswith("_cache") and hasattr(getattr(market, name), "invalidate"):
            getattr(market, name).invalidate()
    yield


def test_treemap_concurrent_requests_hit_kis_once(monkeypatch):
    calls = {"price": 0, "rank": 0}

    async def fake_price(code):
        calls["price"] += 1
        await asyncio.sleep(0.01)
        return {"output": {"hts_kor_isnm": code, "stck_prpr": "100", "prdy_ctrt": "1.5",
                           "hts_avls": "10", "acml_vol": "5", "acml_tr_pbmn": "7"}}

    async def fake_rank():
        calls["rank"] += 1
        return {"output": []}

    monkeypatch.setattr(market, "get_price_data", fake_price)
    monkeypatch.setattr(market.kis_client, "get_institution_foreign_net_buy_ranking", fake_rank)
    monkeypatch.setattr(market, "supabase", FakeSupabase())

    async def go():
        return await asyncio.gather(*[market.get_treemap(sort="change_rate") for _ in range(10)])

    results = run(go())
    universe = {c for codes in market.SECTOR_STOCKS.values() for c in codes}
    assert all(r["status"] == "success" and len(r["data"]) == len(universe) for r in results)
    assert calls["price"] == len(universe)
    assert calls["rank"] == 1

    run(market.get_treemap(sort="frgn_net_buy"))
    assert calls["price"] == len(universe)  # 정렬만 다른 요청도 캐시를 쓴다


def test_treemap_failure_serves_stale_then_recovers(monkeypatch):
    state = {"fail": False}

    async def fake_price(code):
        if state["fail"]:
            raise RuntimeError("kis down")
        return {"output": {"stck_prpr": "100", "prdy_ctrt": "1"}}

    async def fake_rank():
        return {"output": []}

    monkeypatch.setattr(market, "get_price_data", fake_price)
    monkeypatch.setattr(market.kis_client, "get_institution_foreign_net_buy_ranking", fake_rank)
    monkeypatch.setattr(market, "supabase", FakeSupabase())

    first = run(market.get_treemap(sort="change_rate"))
    assert first["data"]

    # TTL 경과 + KIS 전면 장애 + DB fallback도 비어 있음 → 빈 결과는 캐시되지 않고 만료 값을 사용
    market._treemap_cache._clock = lambda t0=market._treemap_cache._clock(): t0 + 400
    state["fail"] = True
    again = run(market.get_treemap(sort="change_rate"))
    assert again["data"] == first["data"]


def test_index_chart_cached_per_market_and_period(monkeypatch):
    calls = []

    async def fake_chart(code, start, end, period):
        calls.append((code, period))
        return {"output2": [{"stck_bsop_date": "20260105", "bstp_nmix_prpr": "2500",
                             "bstp_nmix_oprc": "2490", "bstp_nmix_hgpr": "2510",
                             "bstp_nmix_lwpr": "2480", "acml_vol": "1"}]}

    monkeypatch.setattr(market.kis_client, "get_index_chart", fake_chart)

    async def go():
        await market.get_index_chart(market="KOSPI", period="D")
        await market.get_index_chart(market="KOSPI", period="D")
        await market.get_index_chart(market="KOSDAQ", period="D")
        return await market.get_index_chart(market="KOSPI", period="W")

    out = run(go())
    assert calls == [("0001", "D"), ("1001", "D"), ("0001", "W")]
    assert out["data"][0]["date"] == "2026-01-05"
    assert out["data"][0]["close"] == 2500.0


def test_index_chart_error_returns_generic_message(monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("SECRET")

    monkeypatch.setattr(market.kis_client, "get_index_chart", boom)
    out = run(market.get_index_chart(market="KOSPI", period="D"))
    assert out["status"] == "error" and "SECRET" not in str(out)


def test_investor_trend_cached(monkeypatch):
    calls = []

    async def fake_rank():
        calls.append(1)
        return {"output": [{"mksc_shrn_iscd": "005930", "hts_kor_isnm": "삼성전자",
                            "prdy_ctrt": "1", "frgn_ntby_qty": "100", "orgn_ntby_qty": "50"}]}

    monkeypatch.setattr(market.kis_client, "get_institution_foreign_net_buy_ranking", fake_rank)

    async def go():
        a = await market.get_investor_trend()
        b = await market.get_investor_trend()
        return a, b

    a, b = run(go())
    assert len(calls) == 1
    assert a["data"]["foreign_net_buy"] == 100 and a == b


def test_rankings_empty_result_is_not_cached(monkeypatch):
    calls = []

    async def empty():
        calls.append(1)
        return {"output": []}

    for name in ("get_volume_ranking", "get_trading_amount_ranking", "get_foreign_net_buy_ranking",
                 "get_institution_net_buy_ranking"):
        monkeypatch.setattr(market.kis_client, name, empty)

    async def empty_hl(div):
        calls.append(1)
        return {"output": []}

    monkeypatch.setattr(market.kis_client, "get_52week_high_low", empty_hl)

    async def go():
        await market.get_market_rankings(limit=5)
        await market.get_market_rankings(limit=5)

    run(go())
    assert len(calls) == 12  # 두 번 모두 새로 조회


def test_indices_cached_when_any_price(monkeypatch):
    calls = []

    async def fake_chart(code, start, end, period):
        calls.append(code)
        return {"output1": {"bstp_nmix_prpr": "2500", "bstp_nmix_prdy_vrss": "5",
                            "bstp_nmix_prdy_ctrt": "0.2", "prdy_vrss_sign": "2"}}

    class FakeYahoo:
        async def get(self, url):
            raise RuntimeError("offline")

    monkeypatch.setattr(market.kis_client, "get_index_chart", fake_chart)
    monkeypatch.setattr(market, "_get_yahoo_client", lambda: FakeYahoo())

    async def go():
        a = await market.get_market_indices()
        await market.get_market_indices()
        return a

    out = run(go())
    assert out["data"]["kospi"]["price"] == 2500.0
    assert out["data"]["nasdaq"]["price"] is None
    assert calls == ["0001", "1001"]  # 두 번째 요청은 캐시


def test_sparkline_cached_and_ordered(monkeypatch):
    db = FakeSupabase()
    from datetime import date, timedelta
    today = date.today()
    db.seed("stock_ohlcv", [
        {"stock_code": "005930", "trade_date": (today - timedelta(days=i)).isoformat(), "close_price": 100 + i}
        for i in range(3)
    ])
    monkeypatch.setattr(market, "supabase", db)
    out = run(market.get_sparkline("005930", days=5))
    assert [p["close"] for p in out["data"]] == [102.0, 101.0, 100.0]
    db.tables["stock_ohlcv"].clear()
    assert run(market.get_sparkline("005930", days=5)) == out
