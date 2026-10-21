import json
import logging
import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core import logging_config
from app.core.config import settings
from app.core.errors import internal_error
from app.core.request_context import request_id_var
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
SECRET = "SECRET-DB-PASSWORD-xyz"


def _auth():
    payload = {"sub": "u1", "email": "owner@example.com", "aud": "authenticated",
               "exp": int(time.time()) + 300}
    return {"Authorization": "Bearer " + jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")}


class _Boom:
    def __getattr__(self, name):
        def raiser(*a, **k):
            raise RuntimeError(SECRET)
        return raiser


def test_internal_error_hides_cause_from_client_and_logs_it(caplog):
    with caplog.at_level(logging.ERROR, logger="app.errors"):
        try:
            raise RuntimeError(SECRET)
        except RuntimeError:
            exc = internal_error("조회에 실패했습니다.")
    assert exc.status_code == 500
    assert exc.detail == "조회에 실패했습니다."
    assert SECRET in caplog.text


def test_router_failure_does_not_leak_exception_message(monkeypatch):
    from app.routers import profiles
    monkeypatch.setattr(profiles, "supabase", _Boom())
    r = client.get("/api/v1/profiles", headers=_auth())
    assert r.status_code == 500
    assert r.json()["detail"] == "프로필 목록 조회에 실패했습니다."
    assert SECRET not in r.text


def test_unhandled_exception_returns_standard_body_with_request_id(monkeypatch):
    async def handler():
        raise RuntimeError(SECRET)

    app.add_api_route("/__boom", handler, methods=["GET"])
    try:
        r = client.get("/__boom", headers={"X-Request-ID": "req-123", **_auth()})
    finally:
        app.router.routes.pop()
    body = r.json()
    assert r.status_code == 500
    assert body == {"detail": "서버 내부 오류가 발생했습니다.", "request_id": "req-123"}
    assert r.headers["X-Request-ID"] == "req-123"
    assert SECRET not in r.text


def test_request_id_generated_and_echoed():
    r = client.get("/api/v1/health")
    assert len(r.headers["X-Request-ID"]) == 12
    r2 = client.get("/api/v1/health", headers={"X-Request-ID": "abc"})
    assert r2.headers["X-Request-ID"] == "abc"


def test_request_id_present_on_auth_failure():
    r = client.get("/api/v1/holdings")
    assert r.status_code == 401
    assert r.headers.get("X-Request-ID")


def test_json_formatter_includes_request_id_and_exception():
    token = request_id_var.set("rid-1")
    try:
        record = logging.LogRecord("app.x", logging.ERROR, __file__, 1, "실패 %s", ("원인",), None)
        logging_config.RequestIdFilter().filter(record)
        try:
            raise ValueError("bad")
        except ValueError:
            import sys
            record.exc_info = sys.exc_info()
        data = json.loads(logging_config.JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert data["request_id"] == "rid-1"
    assert data["msg"] == "실패 원인"
    assert data["level"] == "ERROR"
    assert "ValueError" in data["exc"]


def test_setup_logging_honours_env(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("LOG_FORMAT", "json")
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    try:
        logging_config.setup_logging()
        assert root.level == logging.WARNING
        assert isinstance(root.handlers[0].formatter, logging_config.JsonFormatter)
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)


def _boom_route(path):
    async def handler():
        raise RuntimeError("SECRET")
    app.add_api_route(path, handler, methods=["GET"])


def test_unhandled_500_carries_cors_headers_for_allowed_origin():
    _boom_route("/__boom_cors")
    try:
        r = client.get("/__boom_cors", headers={"Origin": "http://localhost:3000", **_auth()})
    finally:
        app.router.routes.pop()
    assert r.status_code == 500
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "X-Request-ID" in r.headers["access-control-expose-headers"]
    assert "SECRET" not in r.text


def test_unhandled_500_has_no_cors_for_unknown_origin():
    _boom_route("/__boom_cors2")
    try:
        r = client.get("/__boom_cors2", headers={"Origin": "https://evil.example", **_auth()})
    finally:
        app.router.routes.pop()
    assert r.status_code == 500
    assert "access-control-allow-origin" not in r.headers


def test_cors_exposes_retry_after_and_request_id_on_normal_responses():
    r = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    exposed = r.headers["access-control-expose-headers"]
    assert "Retry-After" in exposed and "X-Request-ID" in exposed


def test_429_response_is_readable_cross_origin(monkeypatch):
    from app.core.config import settings as s
    monkeypatch.setattr(s, "rate_limit_ip_per_min", 1)
    h = {"Origin": "http://localhost:3000"}
    client.get("/api/v1/holdings", headers=h)
    r = client.get("/api/v1/holdings", headers=h)
    assert r.status_code == 429
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert r.headers["retry-after"].isdigit()
