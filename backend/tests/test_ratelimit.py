import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core import ratelimit
from app.core.config import settings
from app.core.ratelimit import SlidingWindowLimiter
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _offline_db(monkeypatch):
    from app.routers import system
    from tests.fakes import FakeSupabase
    monkeypatch.setattr(system, "supabase", FakeSupabase())


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_allows_up_to_limit_then_blocks_with_retry_after():
    clock = Clock()
    lim = SlidingWindowLimiter(clock=clock)
    assert [lim.hit("k", 3)[0] for _ in range(3)] == [True, True, True]
    ok, retry = lim.hit("k", 3)
    assert ok is False and 1 <= retry <= 61


def test_window_slides():
    clock = Clock()
    lim = SlidingWindowLimiter(clock=clock)
    for _ in range(3):
        lim.hit("k", 3)
    clock.t += 30
    assert lim.hit("k", 3)[0] is False
    clock.t += 31
    assert lim.hit("k", 3)[0] is True


def test_keys_are_independent():
    lim = SlidingWindowLimiter()
    assert lim.hit("a", 1)[0] and lim.hit("b", 1)[0]
    assert not lim.hit("a", 1)[0]


def test_memory_bounded_by_max_keys():
    clock = Clock()
    lim = SlidingWindowLimiter(max_keys=100, clock=clock)
    for i in range(1000):
        clock.t += 0.001
        lim.hit(f"k{i}", 5)
    assert len(lim._hits) <= 100


def test_expired_keys_are_evicted_first():
    clock = Clock()
    lim = SlidingWindowLimiter(max_keys=3, clock=clock)
    lim.hit("old1", 5)
    lim.hit("old2", 5)
    clock.t += 120
    lim.hit("fresh", 5)
    lim.hit("new", 5)
    assert set(lim._hits) == {"fresh", "new"}


class FakeRequest:
    def __init__(self, peer="10.0.0.1", xff=None):
        self.client = type("C", (), {"host": peer})()
        self.headers = {"x-forwarded-for": xff} if xff else {}


@pytest.mark.parametrize("hops,xff,expected", [
    (0, "1.1.1.1, 2.2.2.2", "10.0.0.1"),             # 프록시 미신뢰: 소켓 IP
    (1, "9.9.9.9, 1.1.1.1", "1.1.1.1"),              # 위조된 앞쪽 값 무시, 프록시가 덧붙인 마지막 값
    (2, "9.9.9.9, 1.1.1.1, 2.2.2.2", "1.1.1.1"),
    (1, None, "10.0.0.1"),                           # 헤더 없음 → 소켓 IP
    (3, "1.1.1.1", "10.0.0.1"),                      # 홉 수보다 짧으면 소켓 IP
])
def test_client_ip_resolution(monkeypatch, hops, xff, expected):
    monkeypatch.setattr(settings, "trusted_proxy_hops", hops)
    assert ratelimit.client_ip(FakeRequest(xff=xff)) == expected


def _owner():
    payload = {"sub": "u1", "email": "owner@example.com", "aud": "authenticated",
               "exp": int(time.time()) + 300}
    return {"Authorization": "Bearer " + jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")}


def test_ip_limit_blocks_with_429_and_retry_after(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_ip_per_min", 3)
    codes = [client.get("/api/v1/holdings").status_code for _ in range(5)]
    assert codes == [401, 401, 401, 429, 429]
    r = client.get("/api/v1/holdings")
    assert r.headers["Retry-After"].isdigit()
    assert "다시 시도" in r.json()["detail"]
    assert r.headers.get("X-Request-ID")


def test_health_is_exempt_from_ip_limit(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_ip_per_min", 2)
    assert all(client.get("/api/v1/health").status_code == 200 for _ in range(10))


def test_ip_limit_separates_clients_behind_proxy(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_ip_per_min", 2)
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    a = {"x-forwarded-for": "1.1.1.1"}
    b = {"x-forwarded-for": "2.2.2.2"}
    assert [client.get("/api/v1/holdings", headers=a).status_code for _ in range(3)] == [401, 401, 429]
    assert client.get("/api/v1/holdings", headers=b).status_code == 401


def test_guest_limit_is_per_ip_not_shared(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_guest_per_min", 2)
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    guest = {"X-Guest-Key": settings.guest_api_key}
    one = {**guest, "x-forwarded-for": "1.1.1.1"}
    two = {**guest, "x-forwarded-for": "2.2.2.2"}
    # 게스트 키는 모두가 공유하지만 IP별로 따로 센다
    statuses = [client.get("/api/v1/health/detail", headers=one).status_code for _ in range(3)]
    assert statuses == [200, 200, 429]
    assert client.get("/api/v1/health/detail", headers=two).status_code == 200


def test_guest_write_is_rejected_before_user_limit(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_guest_per_min", 1)
    guest = {"X-Guest-Key": settings.guest_api_key}
    # 읽기 전용 위반은 한도와 무관하게 403 (반복 시도는 IP 전역 한도가 막는다)
    assert [client.post("/api/v1/holdings", headers=guest, json={}).status_code for _ in range(3)] == [403] * 3


def test_user_limit_applies_to_authenticated_owner(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_user_per_min", 2)
    headers = _owner()
    codes = [client.get("/api/v1/health/detail", headers=headers).status_code for _ in range(3)]
    assert codes[:2] == [200, 200] and codes[2] == 429


def test_expensive_endpoint_has_separate_stricter_limit(monkeypatch):
    import app.services.history as history
    import app.services.recommendations as recs

    async def fake_update():
        return []

    monkeypatch.setattr(recs, "update_recommendations", fake_update)
    monkeypatch.setattr(history, "save_snapshot", lambda stocks: None)
    monkeypatch.setattr(settings, "rate_limit_expensive_per_min", 2)
    headers = _owner()
    codes = [client.post("/api/v1/stocks/sync/recommendations", headers=headers).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    # 일반 조회는 영향 없음
    assert client.get("/api/v1/health/detail", headers=headers).status_code == 200


def test_sector_force_is_limited_but_cached_read_is_not(monkeypatch):
    from app.routers import stocks

    async def fake_cached(sector, force=False):
        return [], None

    monkeypatch.setattr(stocks, "get_sector_leaders_cached", fake_cached)
    monkeypatch.setattr(settings, "rate_limit_expensive_per_min", 2)
    sector = next(iter(stocks.SECTOR_STOCKS))
    headers = _owner()
    url = f"/api/v1/stocks/sector-leader?sector={sector}"
    assert all(client.get(url, headers=headers).status_code == 200 for _ in range(6))
    forced = [client.get(url + "&force=true", headers=headers).status_code for _ in range(3)]
    assert forced == [200, 200, 429]


def test_health_detail_reports_client_ip_diagnostics(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    r = client.get("/api/v1/health/detail", headers={**_owner(), "x-forwarded-for": "9.9.9.9, 1.2.3.4"})
    body = r.json()["client"]
    assert body["resolved_ip"] == "1.2.3.4"
    assert body["x_forwarded_for"] == "9.9.9.9, 1.2.3.4"
    assert body["trusted_proxy_hops"] == 1
