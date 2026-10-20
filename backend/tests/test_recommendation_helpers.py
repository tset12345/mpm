from app.services import recommendations as r


def test_to_float_and_to_int_handle_bad_input():
    assert r._to_float("1.5") == 1.5
    assert r._to_float(None) == 0.0
    assert r._to_float("abc", default=7.0) == 7.0
    assert r._to_int("12") == 12
    assert r._to_int("x") == 0
    assert r._to_int(None, default=3) == 3


def test_db_rows_to_ohlcv_sorts_ascending_and_stringifies():
    rows = [
        {"trade_date": "2026-01-03", "close_price": 103, "high_price": 104, "low_price": 102, "volume": 30},
        {"trade_date": "2026-01-01", "close_price": 101, "high_price": 102, "low_price": 100, "volume": 10},
        {"trade_date": "2026-01-02", "close_price": 102, "high_price": 103, "low_price": 101, "volume": 20},
    ]
    out = r._db_rows_to_ohlcv(rows)
    assert [x["stck_clpr"] for x in out] == ["101", "102", "103"]
    assert out[0] == {"stck_clpr": "101", "stck_hgpr": "102", "stck_lwpr": "100", "acml_vol": "10"}


def test_kis_records_to_db_rows_formats_date_and_skips_missing():
    output2 = [
        {"stck_bsop_date": "20260102", "stck_oprc": "100", "stck_hgpr": "110",
         "stck_lwpr": "95", "stck_clpr": "105", "acml_vol": "5000"},
        {"stck_oprc": "1"},
        {"stck_bsop_date": "", "stck_clpr": "1"},
    ]
    rows = r._kis_records_to_db_rows("005930", output2)
    assert rows == [{
        "stock_code": "005930", "trade_date": "2026-01-02",
        "open_price": 100, "high_price": 110, "low_price": 95,
        "close_price": 105, "volume": 5000,
    }]
