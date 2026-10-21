import asyncio
import time

import httpx
import pytest

from app.services import kis_api
from app.services.kis_api import KISApiClient, _RateLimiter


@pytest.fixture
def make_client(monkeypatch, tmp_path):
    monkeypatch.setattr(kis_api, "_TOKEN_CACHE_FILE", tmp_path / "token.json")
    monkeypatch.setattr(kis_api, "_BACKOFF_SEC", 0)

    def build(handler, rate=1000.0, slots=8):
        c = KISApiClient()
        c._access_token = "tok"
        c._token_expires_at = time.time() + 99_999
        c._limiter = _RateLimiter(rate)
        c._slots = asyncio.Semaphore(slots)
        c._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return c

    return build


def run(coro):
    return asyncio.run(coro)


def test_get_sends_headers_and_returns_json(make_client):
    seen = {}

    def handler(req):
        seen["headers"], seen["params"] = req.headers, dict(req.url.params)
        return httpx.Response(200, json={"output": {"stck_prpr": "100"}})

    c = make_client(handler)
    out = run(c.get_stock_price("005930"))
    assert out == {"output": {"stck_prpr": "100"}}
    assert seen["headers"]["authorization"] == "Bearer tok"
    assert seen["headers"]["tr_id"] == "FHKST01010100"
    assert "custtype" not in seen["headers"]
    assert seen["params"]["fid_input_iscd"] == "005930"


def test_custtype_header_sent_for_ranking_calls(make_client):
    seen = {}

    def handler(req):
        seen["custtype"] = req.headers.get("custtype")
        return httpx.Response(200, json={})

    run(make_client(handler).get_volume_ranking())
    assert seen["custtype"] == "P"


def test_retries_server_errors_then_succeeds(make_client):
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(500) if len(calls) < 3 else httpx.Response(200, json={"ok": True})

    assert run(make_client(handler).get_stock_price("1")) == {"ok": True}
    assert len(calls) == 3


def test_gives_up_after_max_attempts(make_client):
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(httpx.HTTPStatusError):
        run(make_client(handler).get_stock_price("1"))
    assert len(calls) == 3


def test_client_errors_are_not_retried(make_client):
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(400)

    with pytest.raises(httpx.HTTPStatusError):
        run(make_client(handler).get_stock_price("1"))
    assert len(calls) == 1


def test_retries_network_errors(make_client):
    calls = []

    def handler(req):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, json={"ok": 1})

    assert run(make_client(handler).get_stock_price("1")) == {"ok": 1}


def test_network_error_raised_after_all_attempts(make_client):
    def handler(req):
        raise httpx.ConnectError("down")

    with pytest.raises(httpx.ConnectError):
        run(make_client(handler).get_stock_price("1"))


def test_401_refreshes_token_once(make_client):
    state = {"token_calls": 0, "api_calls": 0}

    def handler(req):
        if req.url.path.endswith("/oauth2/tokenP"):
            state["token_calls"] += 1
            return httpx.Response(200, json={"access_token": "new", "expires_in": 86400})
        state["api_calls"] += 1
        if req.headers["authorization"] == "Bearer tok":
            return httpx.Response(401)
        return httpx.Response(200, json={"ok": "fresh"})

    c = make_client(handler)
    assert run(c.get_stock_price("1")) == {"ok": "fresh"}
    assert state == {"token_calls": 1, "api_calls": 2}


def test_persistent_401_is_not_looped(make_client):
    state = {"api_calls": 0}

    def handler(req):
        if req.url.path.endswith("/oauth2/tokenP"):
            return httpx.Response(200, json={"access_token": "new", "expires_in": 86400})
        state["api_calls"] += 1
        return httpx.Response(401)

    with pytest.raises(httpx.HTTPStatusError):
        run(make_client(handler).get_stock_price("1"))
    assert state["api_calls"] == 2


def test_rate_limiter_spaces_requests():
    async def go():
        limiter = _RateLimiter(50.0)
        started = time.monotonic()
        await asyncio.gather(*[limiter.acquire() for _ in range(10)])
        return time.monotonic() - started

    assert run(go()) >= 9 * 0.02 * 0.9


def test_concurrency_never_exceeds_slot_limit(make_client):
    state = {"now": 0, "peak": 0}

    async def handler(req):
        state["now"] += 1
        state["peak"] = max(state["peak"], state["now"])
        await asyncio.sleep(0.01)
        state["now"] -= 1
        return httpx.Response(200, json={})

    c = make_client(handler, slots=3)

    async def go():
        await asyncio.gather(*[c.get_stock_price(str(i)) for i in range(15)])

    run(go())
    assert state["peak"] <= 3
    assert state["peak"] >= 2


def test_auto_rate_depends_on_mock_flag(monkeypatch):
    monkeypatch.setattr(kis_api.settings, "kis_max_rps", 0)
    monkeypatch.setattr(kis_api.settings, "kis_is_mock", True)
    assert KISApiClient()._limiter.interval == pytest.approx(0.5)
    monkeypatch.setattr(kis_api.settings, "kis_is_mock", False)
    assert KISApiClient()._limiter.interval == pytest.approx(1 / 15)
    monkeypatch.setattr(kis_api.settings, "kis_max_rps", 5)
    assert KISApiClient()._limiter.interval == pytest.approx(0.2)
