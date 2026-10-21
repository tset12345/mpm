import time

import jwt
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.routers import system
from tests.fakes import FakeSupabase

client = TestClient(app, raise_server_exceptions=False)


def _auth():
    payload = {"sub": "u1", "email": "owner@example.com", "aud": "authenticated",
               "exp": int(time.time()) + 300}
    return {"Authorization": "Bearer " + jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")}


def test_health_detail_requires_auth():
    assert client.get("/api/v1/health/detail").status_code == 401


def test_health_detail_reports_freshness_and_db(monkeypatch):
    db = FakeSupabase()
    db.seed("stock_recommendations", [{"date": "2026-10-19"}, {"date": "2026-10-20"}])
    db.seed("stock_ohlcv", [{"trade_date": "2026-10-20"}])
    monkeypatch.setattr(system, "supabase", db)
    r = client.get("/api/v1/health/detail", headers=_auth())
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok"
    assert body["version"] == app.version
    assert body["checks"]["db"]["ok"] is True
    assert body["data_freshness"] == {"recommendations_date": "2026-10-20", "ohlcv_date": "2026-10-20"}
    assert body["scheduler"]["running"] is False
    assert body["uptime_sec"] >= 0


def test_health_detail_degraded_when_db_down(monkeypatch):
    class Down:
        def table(self, name):
            raise RuntimeError("db down")

    monkeypatch.setattr(system, "supabase", Down())
    r = client.get("/api/v1/health/detail", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    assert body["checks"]["db"] == {"ok": False}
    assert body["data_freshness"] == {}
    assert "db down" not in r.text


def test_public_health_stays_minimal():
    assert client.get("/api/v1/health").json() == {"status": "ok"}
