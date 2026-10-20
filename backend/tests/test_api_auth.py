import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)

PROTECTED = "/api/v1/holdings"


def _token(email="owner@example.com", exp_offset=300, audience="authenticated", secret=None):
    payload = {"sub": "u1", "email": email, "aud": audience, "exp": int(time.time()) + exp_offset}
    return jwt.encode(payload, secret or settings.supabase_jwt_secret, algorithm="HS256")


def test_health_is_public_for_get_and_head():
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert client.head("/api/v1/health").status_code == 200


def test_protected_route_requires_auth():
    assert client.get(PROTECTED).status_code == 401


@pytest.mark.parametrize("path", [
    "/api/v1/stocks/recommend", "/api/v1/virtual/accounts", "/api/v1/market/indices",
    "/api/v1/profiles", "/api/v1/portfolio/analysis", "/api/v1/analysis/005930",
])
def test_every_router_rejects_anonymous(path):
    assert client.get(path).status_code == 401


def test_invalid_and_wrong_audience_tokens_rejected():
    assert client.get(PROTECTED, headers={"Authorization": "Bearer garbage"}).status_code == 401
    bad_aud = _token(audience="other")
    assert client.get(PROTECTED, headers={"Authorization": f"Bearer {bad_aud}"}).status_code == 401


def test_expired_token_rejected():
    tok = _token(exp_offset=-10)
    r = client.get(PROTECTED, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Token expired"


def test_token_signed_with_wrong_secret_rejected():
    tok = _token(secret="x" * 40)
    assert client.get(PROTECTED, headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_non_whitelisted_email_forbidden():
    tok = _token(email="stranger@example.com")
    r = client.get(PROTECTED, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


def test_valid_owner_token_passes_auth(monkeypatch):
    from app.routers import holdings

    class _Res:
        data = []

    class _Q:
        def __getattr__(self, name):
            return lambda *a, **k: self

        def execute(self):
            return _Res()

    monkeypatch.setattr(holdings.supabase, "table", lambda name: _Q())
    tok = _token()
    r = client.get(PROTECTED, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code != 401 and r.status_code != 403


def test_ampm_key_is_read_only():
    h = {"X-AMPM-Key": settings.ampm_api_key}
    assert client.post(PROTECTED, headers=h, json={}).status_code == 403
    assert client.get(PROTECTED, headers={"X-AMPM-Key": "wrong"}).status_code == 401


def test_guest_key_is_read_only():
    h = {"X-Guest-Key": settings.guest_api_key}
    assert client.post(PROTECTED, headers=h, json={}).status_code == 403
    assert client.delete(f"{PROTECTED}/1", headers=h).status_code == 403
    assert client.get(PROTECTED, headers={"X-Guest-Key": "wrong"}).status_code == 401
