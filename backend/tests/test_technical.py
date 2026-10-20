import pytest

from app.services import technical as t
from tests.conftest import make_records


def test_sma_basic_and_insufficient():
    assert t.sma([1, 2, 3, 4, 5], 5) == 3.0
    assert t.sma([1, 2, 3, 4, 5], 2) == 4.5
    assert t.sma([1, 2], 5) is None


def test_ema_series_length_and_constant_input():
    series = t.ema_series([10.0] * 30, 12)
    assert len(series) == 30 - 12 + 1
    assert all(v == pytest.approx(10.0) for v in series)
    assert t.ema_series([1.0, 2.0], 5) == []


def test_rsi_monotonic_series():
    assert t.rsi([float(i) for i in range(1, 40)]) == 100.0
    assert t.rsi([float(i) for i in range(40, 1, -1)]) == pytest.approx(0.0)
    assert t.rsi([1.0] * 5) is None


def test_bollinger_constant_series_collapses_to_mid():
    upper, mid, lower = t.bollinger([50.0] * 20)
    assert upper == mid == lower == 50.0
    assert t.bollinger([1.0] * 5) is None


def test_bollinger_band_symmetry():
    closes = [100.0 + (i % 5) for i in range(40)]
    upper, mid, lower = t.bollinger(closes)
    assert upper - mid == pytest.approx(mid - lower)
    assert upper > mid > lower


def test_atr_constant_true_range():
    closes = [100.0] * 30
    highs = [101.0] * 30
    lows = [99.0] * 30
    assert t.atr(highs, lows, closes, 14) == pytest.approx(2.0)
    assert t.atr(highs[:5], lows[:5], closes[:5], 14) is None


def test_volume_ratio_all_up_days_caps_at_300():
    closes = [float(100 + i) for i in range(30)]
    volumes = [1000.0] * 30
    assert t.volume_ratio(closes, volumes, 20) == 300.0
    assert t.volume_ratio(closes[:10], volumes[:10], 20) is None


def test_analyze_returns_empty_when_too_few_records():
    result = t.analyze(make_records([100.0] * 10))
    assert result["score"] == 0
    assert result["engine"] is None
    assert result["strength"] == "약함"


def test_analyze_low_volume_hard_filter():
    records = make_records([100.0 + i for i in range(60)], volumes=[1_000] * 60)
    result = t.analyze(records)
    assert result["score"] == 0
    assert result["filter_failed"] == "low_volume"


def test_analyze_bear_market_zeroes_engine_a():
    closes = [100.0 + i * 0.5 for i in range(80)]
    result = t.analyze(make_records(closes), market_regime="BEAR")
    assert result["engine_a_score"] == 0


def test_analyze_output_contract():
    closes = [100.0 + i * 0.5 + (i % 3) for i in range(80)]
    result = t.analyze(make_records(closes))
    assert 0 <= result["score"] <= 100
    assert result["score"] == max(result["engine_a_score"], result["engine_b_score"])
    assert result["engine"] in ("A", "B")
    assert result["strength"] in ("약함", "보통", "강함", "매우 강함")
    assert result["score_detail"] == {
        "engine_a": result["engine_a_score"],
        "engine_b": result["engine_b_score"],
    }
    for key in ("ma5", "ma20", "rsi", "atr", "volume_ma20", "cloud_position"):
        assert key in result["signals"]


@pytest.mark.parametrize("score,label", [(0, "약함"), (24, "약함"), (25, "보통"), (50, "강함"), (75, "매우 강함")])
def test_strength_thresholds(monkeypatch, score, label):
    monkeypatch.setattr(t, "_engine_a", lambda *a, **k: (score, []))
    monkeypatch.setattr(t, "_engine_b", lambda *a, **k: (0, []))
    result = t.analyze(make_records([100.0 + i * 0.1 for i in range(80)]))
    assert result["score"] == score
    assert result["strength"] == label


def test_engine_a_wins_ties(monkeypatch):
    monkeypatch.setattr(t, "_engine_a", lambda *a, **k: (40, ["A"]))
    monkeypatch.setattr(t, "_engine_b", lambda *a, **k: (40, ["B"]))
    result = t.analyze(make_records([100.0 + i * 0.1 for i in range(80)]))
    assert result["engine"] == "A"
    assert result["tags"] == ["A"]
