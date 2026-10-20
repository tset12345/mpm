from app.services import ichimoku
from app.services.expected_return import compute


def _series(closes):
    return [c + 1 for c in closes], [c - 1 for c in closes], list(closes)


def test_ichimoku_insufficient_data_is_unknown():
    highs, lows, closes = _series([100.0] * 30)
    assert ichimoku.calculate(highs, lows, closes)["position"] == "unknown"


def test_ichimoku_uptrend_is_above_cloud():
    highs, lows, closes = _series([100.0 + i for i in range(52)])
    result = ichimoku.calculate(highs, lows, closes)
    assert result["conversion_line"] == 147
    assert result["span_b"] == 126
    assert result["position"] == "above_cloud"


def test_ichimoku_downtrend_is_below_cloud():
    highs, lows, closes = _series([151.0 - i for i in range(52)])
    assert ichimoku.calculate(highs, lows, closes)["position"] == "below_cloud"


def test_ichimoku_flat_is_in_cloud():
    highs, lows, closes = _series([100.0] * 52)
    assert ichimoku.calculate(highs, lows, closes)["position"] == "in_cloud"


def test_expected_return_approves_high_reward():
    r = compute(current_price=10_000, eps=1_000, bps=None, roe=None)
    assert r["target_price"] == 15_000
    assert r["target_upside"] == 50.0
    assert r["stop_loss"] == 9_000
    assert r["expected_value"] == 26.0
    assert r["risk_reward"] == 5.0
    assert r["verdict"] == "진입 승인"


def test_expected_return_holds_when_target_below_price():
    r = compute(current_price=10_000, eps=500, bps=None, roe=None)
    assert r["verdict"] == "진입 보류"
    assert r["expected_value"] is None


def test_expected_return_rejects_low_risk_reward():
    r = compute(current_price=10_000, eps=1_100, bps=None, roe=None)
    assert r["target_price"] == 16_500
    r = compute(current_price=10_000, eps=1_100, bps=None, roe=None, stop_loss=7_000)
    assert r["risk_reward"] == 2.17
    r = compute(current_price=10_000, eps=1_100, bps=None, roe=None, stop_loss=3_000)
    assert r["risk_reward"] == 0.93
    assert r["verdict"] == "진입 보류"
    assert "기준 미달" in r["verdict_reason"]


def test_expected_return_pbr_roe_and_average():
    r = compute(current_price=10_000, eps=1_000, bps=20_000, roe=8.0, coe=0.08)
    assert r["target_price_per"] == 15_000
    assert r["target_price_pbr"] == 20_000
    assert r["target_price"] == 17_500


def test_expected_return_without_inputs_returns_no_verdict():
    r = compute(current_price=10_000, eps=None, bps=None, roe=None)
    assert r["target_price"] is None
    assert r["verdict"] is None
    assert r["stop_loss"] == 9_000


def test_expected_return_invalid_stop_loss_falls_back():
    r = compute(current_price=10_000, eps=None, bps=None, roe=None, stop_loss=12_000)
    assert r["stop_loss"] == 9_000
    r = compute(current_price=10_000, eps=None, bps=None, roe=None, stop_loss=9_500)
    assert r["stop_loss"] == 9_500
    assert r["stop_loss_rate"] == -5.0
