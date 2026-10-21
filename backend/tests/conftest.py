import os
import sys
from pathlib import Path

# app 모듈이 import 시점에 Supabase 클라이언트를 만들므로 가짜 값을 먼저 주입한다
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJyb2xlIjoic2VydmljZV9yb2xlIn0.c2lnbmF0dXJl"
)
os.environ["SUPABASE_JWT_SECRET"] = "test-jwt-secret-with-sufficient-length-32b"
os.environ["ALLOWED_USER_EMAIL"] = "owner@example.com"
os.environ["AMPM_API_KEY"] = "ampm-test-key"
os.environ["GUEST_API_KEY"] = "guest-test-key"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["ENABLE_INTRADAY"] = "false"
os.environ["ENABLE_TELEGRAM"] = "false"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def make_records(closes, highs=None, lows=None, volumes=None, opens=None):
    """technical.analyze / sell_signal 입력 형식(KIS 문자열 필드)으로 변환."""
    n = len(closes)
    highs = highs or [c * 1.01 for c in closes]
    lows = lows or [c * 0.99 for c in closes]
    volumes = volumes or [1_000_000] * n
    opens = opens or list(closes)
    return [
        {
            "stck_clpr": str(c), "stck_hgpr": str(h), "stck_lwpr": str(l),
            "stck_oprc": str(o), "acml_vol": str(v),
        }
        for c, h, l, o, v in zip(closes, highs, lows, opens, volumes)
    ]


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from app.core.ratelimit import limiter
    limiter.clear()
    yield
    limiter.clear()
