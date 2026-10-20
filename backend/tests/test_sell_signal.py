import math

from app.services import sell_signal as s
from tests.conftest import make_records


def test_dead_cross_detected_within_lookback():
    closes = [100.0] * 25 + [120.0] * 5 + [80.0] * 3
    assert s._dead_cross(closes, 5, 20) is True


def test_dead_cross_not_detected_in_uptrend():
    closes = [100.0 + i for i in range(40)]
    assert s._dead_cross(closes, 5, 20) is False


def test_dead_cross_requires_enough_history():
    assert s._dead_cross([100.0] * 10, 5, 20) is False


def test_macd_dead_cross_false_on_short_history():
    assert s._macd_dead_cross([100.0] * 20) is False


def test_macd_dead_cross_detected_only_near_the_cross():
    base = [100.0 + 10 * math.sin(i / 6) for i in range(120)]
    assert s._macd_dead_cross(base[:55], lookback=3) is True
    assert s._macd_dead_cross(base[:49], lookback=3) is False
    assert s._macd_dead_cross(base[:63], lookback=3) is False


def test_macd_dead_cross_false_in_steady_uptrend():
    assert s._macd_dead_cross([100.0 + i for i in range(60)], lookback=3) is False


def test_bearish_candle_volume():
    opens = [100.0] * 25
    closes = [100.0] * 24 + [95.0]
    volumes = [1000.0] * 24 + [2000.0]
    assert s._bearish_candle_volume(opens, closes, volumes) is True
    assert s._bearish_candle_volume(opens, closes, [1000.0] * 25) is False
    assert s._bearish_candle_volume(opens, [100.0] * 25, volumes) is False
    assert s._bearish_candle_volume(opens[:10], closes[:10], volumes[:10]) is False


def test_extract_series_skips_bad_rows():
    records = make_records([100.0, 101.0]) + [{"stck_clpr": "abc"}]
    closes, opens, highs, lows, volumes = s._extract_series(records)
    assert closes == [100.0, 101.0]
    assert len(opens) == len(highs) == len(lows) == len(volumes) == 2


def test_sell_levels_stop_loss_and_targets():
    levels = s._sell_levels(10_000, 1_000.0, [100.0, 200.0, 150.0], 120, 250)
    assert levels["stop_loss_5"] == 9_500
    assert levels["stop_loss_10"] == 9_000
    assert levels["stop_loss_15"] == 8_500
    assert levels["trailing_high_ref"] == 200
    assert levels["trailing_stop_7"] == 186
    assert levels["target_per15"] == 15_000
    assert levels["w52_high"] == 250


def test_sell_levels_without_optional_inputs():
    levels = s._sell_levels(10_000, None, [], None, None)
    assert set(levels) == {"stop_loss_5", "stop_loss_10", "stop_loss_15"}


def test_analyze_sell_output_contract_and_grade():
    closes = [100.0 + i * 0.3 for i in range(80)]
    result = s.analyze_sell(make_records(closes), avg_price=110, current_price=int(closes[-1]))
    assert 0 <= result["sell_score"] <= 100
    assert result["grade"] in ("관망", "주의", "매도 검토", "즉시 매도")
    assert isinstance(result["signals"], list)
    assert result["sell_levels"]["stop_loss_10"] == 99


def test_analyze_sell_flags_deeper_loss_as_more_urgent():
    closes = [100.0 - i * 0.6 for i in range(80)]
    records = make_records(closes)
    calm = s.analyze_sell(make_records([100.0 + i * 0.3 for i in range(80)]), 110, 120)
    falling = s.analyze_sell(records, avg_price=100, current_price=int(closes[-1]))
    assert falling["sell_score"] > calm["sell_score"]
