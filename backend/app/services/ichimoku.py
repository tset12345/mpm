from datetime import date, timedelta


def calculate(highs: list[float], lows: list[float], closes: list[float]) -> dict:
    """
    일목균형표 계산 (데이터는 오래된 순 정렬 필요)
    - 전환선: (9일 최고 + 9일 최저) / 2
    - 기준선: (26일 최고 + 26일 최저) / 2
    - 선행스팬A: (전환선 + 기준선) / 2
    - 선행스팬B: (52일 최고 + 52일 최저) / 2
    """
    n = len(highs)
    if n < 52:
        return {"conversion_line": 0, "base_line": 0, "span_a": 0, "span_b": 0, "position": "unknown"}

    def midpoint(period: int) -> float:
        h = max(highs[-period:])
        l = min(lows[-period:])
        return (h + l) / 2

    conversion = midpoint(9)
    base = midpoint(26)
    span_a = (conversion + base) / 2
    span_b = midpoint(52)

    current_price = closes[-1]
    cloud_top = max(span_a, span_b)
    cloud_bottom = min(span_a, span_b)

    if current_price > cloud_top:
        position = "above_cloud"
    elif current_price < cloud_bottom:
        position = "below_cloud"
    else:
        position = "in_cloud"

    return {
        "conversion_line": round(conversion),
        "base_line": round(base),
        "span_a": round(span_a),
        "span_b": round(span_b),
        "position": position,
    }


async def fetch_and_calculate(stock_code: str, kis_client) -> dict:
    """KIS API에서 60일 OHLCV를 가져와 일목균형표를 계산합니다."""
    today = date.today()
    start = (today - timedelta(days=90)).strftime("%Y%m%d")  # 여유있게 90일
    end = today.strftime("%Y%m%d")

    try:
        data = await kis_client.get_daily_ohlcv(stock_code, start, end)
        records = data.get("output2", [])
    except Exception:
        return {"conversion_line": 0, "base_line": 0, "span_a": 0, "span_b": 0, "position": "unknown"}

    if not records:
        return {"conversion_line": 0, "base_line": 0, "span_a": 0, "span_b": 0, "position": "unknown"}

    # KIS API는 최신순으로 반환 → 오래된 순으로 뒤집기
    records = list(reversed(records))

    highs, lows, closes = [], [], []
    for r in records:
        try:
            highs.append(float(r.get("stck_hgpr") or 0))
            lows.append(float(r.get("stck_lwpr") or 0))
            closes.append(float(r.get("stck_clpr") or 0))
        except (ValueError, TypeError):
            continue

    return calculate(highs, lows, closes)
