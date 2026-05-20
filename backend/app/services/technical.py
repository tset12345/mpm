"""
Technical analysis scoring module for MPM recommendation engine.
All indicator functions operate on chronologically sorted data (oldest first).
Scoring: 4 categories × max 10 points = 40 total.
"""

import math


# ── Basic building blocks ──────────────────────────────────────────────────────

def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_series(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    k = 2.0 / (period + 1)
    series = [sum(values[:period]) / period]
    for v in values[period:]:
        series.append(v * k + series[-1] * (1 - k))
    return series


def _rma(series: list[float], period: int) -> list[float]:
    """Wilder's Smoothed MA seeded with SMA; k = 1/period."""
    if len(series) < period:
        return []
    alpha = 1.0 / period
    result = [sum(series[:period]) / period]
    for v in series[period:]:
        result.append(result[-1] * (1 - alpha) + v * alpha)
    return result


def rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))


def stochastic(
    highs: list[float], lows: list[float], closes: list[float],
    k_period: int = 14, d_period: int = 3,
) -> tuple[float | None, float | None]:
    if len(closes) < k_period + d_period - 1:
        return None, None
    raw_k = []
    for i in range(k_period - 1, len(closes)):
        wh = max(highs[i - k_period + 1: i + 1])
        wl = min(lows[i - k_period + 1: i + 1])
        denom = wh - wl
        raw_k.append(100.0 * (closes[i] - wl) / denom if denom != 0 else 50.0)
    if len(raw_k) < d_period:
        return None, None
    slow_k = [sum(raw_k[i - d_period + 1: i + 1]) / d_period for i in range(d_period - 1, len(raw_k))]
    if len(slow_k) < d_period:
        return None, None
    return slow_k[-1], sum(slow_k[-d_period:]) / d_period


def bollinger(
    closes: list[float], period: int = 20, std_multiplier: float = 2.0
) -> tuple[float, float, float] | None:
    if len(closes) < period:
        return None
    window = closes[-period:]
    mid = sum(window) / period
    std = math.sqrt(sum((x - mid) ** 2 for x in window) / period)
    return mid + std_multiplier * std, mid, mid - std_multiplier * std


def _macd_series(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[list[float], list[float]] | None:
    fast_ema = ema_series(closes, fast)
    slow_ema = ema_series(closes, slow)
    if not fast_ema or not slow_ema:
        return None
    offset = slow - fast
    if len(fast_ema) <= offset:
        return None
    macd_line = [f - s for f, s in zip(fast_ema[offset:], slow_ema)]
    if len(macd_line) < signal:
        return None
    signal_line = ema_series(macd_line, signal)
    return (macd_line, signal_line) if signal_line else None


def atr(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> float | None:
    if len(closes) < period + 1:
        return None
    tr_series = [
        max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        for i in range(1, len(closes))
    ]
    smoothed = _rma(tr_series, period)
    return smoothed[-1] if smoothed else None


def dmi(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> tuple[float | None, float | None, float | None]:
    if len(closes) < 2 * period + 1:
        return None, None, None
    tr_series, plus_dm, minus_dm = [], [], []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_series.append(tr)
        up = highs[i] - highs[i - 1]
        dn = lows[i - 1] - lows[i]
        plus_dm.append(up if up > dn and up > 0 else 0.0)
        minus_dm.append(dn if dn > up and dn > 0 else 0.0)
    atr14 = _rma(tr_series, period)
    plus_dm14 = _rma(plus_dm, period)
    minus_dm14 = _rma(minus_dm, period)
    if not atr14:
        return None, None, None
    dx_series = []
    for a, p, m in zip(atr14, plus_dm14, minus_dm14):
        if a == 0:
            continue
        pdi, mdi = 100 * p / a, 100 * m / a
        total = pdi + mdi
        dx_series.append(100 * abs(pdi - mdi) / total if total != 0 else 0.0)
    adx_series = _rma(dx_series, period)
    if not adx_series or atr14[-1] == 0:
        return None, None, None
    return (100 * plus_dm14[-1] / atr14[-1],
            100 * minus_dm14[-1] / atr14[-1],
            adx_series[-1])


def cci(
    highs: list[float], lows: list[float], closes: list[float], period: int = 20
) -> float | None:
    if len(closes) < period:
        return None
    tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    window = tp[-period:]
    mean_tp = sum(window) / period
    mean_dev = sum(abs(v - mean_tp) for v in window) / period
    if mean_dev == 0:
        return 0.0
    return (window[-1] - mean_tp) / (0.015 * mean_dev)


def obv_series(closes: list[float], volumes: list[float]) -> list[float]:
    if len(closes) < 2 or len(volumes) != len(closes):
        return []
    result = [volumes[0]]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            result.append(result[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            result.append(result[-1] - volumes[i])
        else:
            result.append(result[-1])
    return result


def obv(closes: list[float], volumes: list[float]) -> float | None:
    s = obv_series(closes, volumes)
    return s[-1] if s else None


# ── New indicators ─────────────────────────────────────────────────────────────

def mfi(
    highs: list[float], lows: list[float], closes: list[float],
    volumes: list[float], period: int = 14
) -> float | None:
    """Money Flow Index."""
    if len(closes) < period + 1:
        return None
    tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    rmf = [t * v for t, v in zip(tp, volumes)]
    pos_flow = neg_flow = 0.0
    for i in range(len(closes) - period, len(closes)):
        if tp[i] > tp[i - 1]:
            pos_flow += rmf[i]
        elif tp[i] < tp[i - 1]:
            neg_flow += rmf[i]
    if neg_flow == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + pos_flow / neg_flow)


def chaikin_osc(
    highs: list[float], lows: list[float], closes: list[float],
    volumes: list[float], fast: int = 3, slow: int = 10
) -> float | None:
    """Chaikin Oscillator = EMA(ADL, fast) - EMA(ADL, slow)."""
    if len(closes) < slow:
        return None
    cum = 0.0
    adl = []
    for h, l, c, v in zip(highs, lows, closes, volumes):
        denom = h - l
        mfm = ((c - l) - (h - c)) / denom if denom != 0 else 0.0
        cum += mfm * v
        adl.append(cum)
    fast_ema = ema_series(adl, fast)
    slow_ema = ema_series(adl, slow)
    if not fast_ema or not slow_ema:
        return None
    return fast_ema[-1] - slow_ema[-1]


def parabolic_sar(
    highs: list[float], lows: list[float],
    af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2
) -> tuple[float | None, bool]:
    """
    Parabolic SAR.
    Returns (sar_value, is_bullish) where is_bullish = price above SAR.
    """
    n = len(highs)
    if n < 3:
        return None, False
    is_bull = highs[1] > highs[0]
    ep = highs[1] if is_bull else lows[1]
    sar = lows[0] if is_bull else highs[0]
    af = af_start
    for i in range(2, n):
        new_sar = sar + af * (ep - sar)
        if is_bull:
            new_sar = min(new_sar, lows[i - 1], lows[i - 2])
        else:
            new_sar = max(new_sar, highs[i - 1], highs[i - 2])
        sar = new_sar
        if is_bull:
            if lows[i] < sar:
                is_bull, sar, ep, af = False, ep, lows[i], af_start
            elif highs[i] > ep:
                ep = highs[i]
                af = min(af + af_step, af_max)
        else:
            if highs[i] > sar:
                is_bull, sar, ep, af = True, ep, highs[i], af_start
            elif lows[i] < ep:
                ep = lows[i]
                af = min(af + af_step, af_max)
    return sar, is_bull


def envelope(
    closes: list[float], period: int = 20, pct: float = 0.05
) -> tuple[float, float, float] | None:
    """Envelope bands: (upper, middle, lower) = (MA*(1+pct), MA, MA*(1-pct))."""
    if len(closes) < period:
        return None
    ma = sum(closes[-period:]) / period
    return ma * (1 + pct), ma, ma * (1 - pct)


def pivot_point(high: float, low: float, close: float) -> dict:
    """Classic Pivot Point from previous period's H/L/C."""
    pp = (high + low + close) / 3
    return {
        "pp": pp,
        "r1": 2 * pp - low,
        "r2": pp + (high - low),
        "s1": 2 * pp - high,
        "s2": pp - (high - low),
    }


def volume_ratio(closes: list[float], volumes: list[float], period: int = 20) -> float | None:
    """
    Volume Ratio (VR) = (up_vol + 0.5*flat_vol) / (down_vol + 0.5*flat_vol) × 100.
    VR < 70 = oversold, VR > 150 = overbought.
    """
    if len(closes) < period + 1 or len(volumes) < period + 1:
        return None
    up_vol = flat_vol = down_vol = 0.0
    for i in range(len(closes) - period, len(closes)):
        if closes[i] > closes[i - 1]:
            up_vol += volumes[i]
        elif closes[i] < closes[i - 1]:
            down_vol += volumes[i]
        else:
            flat_vol += volumes[i]
    denom = down_vol + 0.5 * flat_vol
    if denom == 0:
        return 300.0
    return (up_vol + 0.5 * flat_vol) / denom * 100


def _rsi_bullish_divergence(
    closes: list[float], period: int = 14, lookback: int = 20
) -> bool:
    """Bullish RSI divergence: price lower low while RSI makes higher low."""
    if len(closes) < period + lookback + 5:
        return False
    recent_window = closes[-5:]
    recent_low_price = min(recent_window)
    recent_low_idx = len(closes) - 5 + recent_window.index(recent_low_price)
    prev_window = closes[-lookback:-5]
    if not prev_window:
        return False
    prev_low_price = min(prev_window)
    prev_low_idx = len(closes) - lookback + prev_window.index(prev_low_price)
    if recent_low_price >= prev_low_price:
        return False
    rsi_recent = rsi(closes[:recent_low_idx + 1], period)
    rsi_prev = rsi(closes[:prev_low_idx + 1], period)
    if rsi_recent is None or rsi_prev is None:
        return False
    return rsi_recent > rsi_prev


# ── Main scoring function ──────────────────────────────────────────────────────

def analyze(records: list[dict], cloud_position: str = "unknown") -> dict:
    """
    Technical analysis scoring: 4 categories × max 10 pts = 40 total.

    Args:
        records: OHLCV dicts sorted oldest-first (keys: stck_hgpr, stck_lwpr, stck_clpr, acml_vol).
        cloud_position: Ichimoku position ("above_cloud" | "in_cloud" | "below_cloud" | "unknown").
    """
    EMPTY: dict = {
        "score": 0, "tags": [], "signals": {},
        "score_detail": {"trend": 0, "momentum": 0, "volatility": 0, "volume": 0},
        "strength": "약함",
    }

    if len(records) < 30:
        return EMPTY

    closes, highs, lows, volumes = [], [], [], []
    for r in records:
        try:
            closes.append(float(r.get("stck_clpr") or 0))
            highs.append(float(r.get("stck_hgpr") or 0))
            lows.append(float(r.get("stck_lwpr") or 0))
            volumes.append(float(r.get("acml_vol") or 0))
        except (ValueError, TypeError):
            continue

    if len(closes) < 30:
        return EMPTY

    tags: list[str] = []
    signals: dict = {}
    cur = closes[-1]

    # ── A. 추세 분석 (max 10) ─────────────────────────────────────────────────
    a = 0

    ma5 = sma(closes, 5)
    ma20 = sma(closes, 20)
    ma60 = sma(closes, 60) if len(closes) >= 60 else None
    signals.update({"ma5": ma5, "ma20": ma20, "ma60": ma60})

    # MA 정배열 / 골든크로스 (+2)
    if ma5 is not None and ma20 is not None:
        aligned = (ma60 is not None and ma5 > ma20 > ma60) or (ma60 is None and ma5 > ma20)
        crossed = False
        for offset in range(1, 4):
            if len(closes) >= offset + 20:
                pm5 = sma(closes[:-offset], 5)
                pm20 = sma(closes[:-offset], 20)
                if pm5 is not None and pm20 is not None and pm5 <= pm20 and ma5 > ma20:
                    crossed = True
                    break
        if aligned or crossed:
            a += 2
            tags.append("골든크로스")

    # MACD 상향돌파 (+2) / 오실레이터 양전 (+1)
    macd_result = _macd_series(closes)
    macd_val = macd_sig = None
    if macd_result is not None:
        ml, sl = macd_result
        if len(ml) >= 2 and len(sl) >= 2:
            macd_val, macd_sig = ml[-1], sl[-1]
            if ml[-1] > sl[-1] and ml[-2] <= sl[-2]:
                a += 2
                tags.append("MACD 상향돌파")
            if (ml[-1] - sl[-1]) > 0 and (ml[-2] - sl[-2]) <= 0:
                a += 1
                tags.append("MACD 오실레이터 양전")
        else:
            macd_val = ml[-1] if ml else None
            macd_sig = sl[-1] if sl else None
    signals.update({"macd": macd_val, "macd_signal": macd_sig})

    # 이격도 저점 (+1)
    disparity = cur / ma20 * 100 if ma20 else None
    signals["disparity"] = disparity
    if disparity is not None and disparity < 97:
        a += 1
        tags.append("이격도 저점")

    # DMI / ADX: 강한 상승추세 (+2)
    plus_di, minus_di, adx = dmi(highs, lows, closes, 14)
    signals.update({"adx": adx, "plus_di": plus_di, "minus_di": minus_di})
    if adx is not None and plus_di is not None and minus_di is not None:
        if adx >= 20 and plus_di > minus_di:
            a += 2
            tags.append("강한 상승추세")

    # 일목 구름대 돌파 (+2)
    if cloud_position == "above_cloud":
        a += 2
        tags.append("일목 구름대 돌파")

    # Parabolic SAR 매수전환: +2 if just reversed to bullish, +1 if continuing
    sar_val, sar_bull = parabolic_sar(highs, lows)
    signals["parabolic_sar"] = sar_val
    if sar_val is not None and sar_bull:
        if len(highs) >= 4:
            _, prev_bull = parabolic_sar(highs[:-1], lows[:-1])
            if not prev_bull:
                a += 2
                tags.append("Parabolic 매수전환")
            else:
                a += 1
        else:
            a += 1

    a = min(a, 10)

    # ── B. 모멘텀 분석 (max 10) ──────────────────────────────────────────────
    b = 0

    rsi_val = rsi(closes, 14)
    signals["rsi"] = rsi_val
    if rsi_val is not None:
        if rsi_val >= 30 and len(closes) >= 2:
            prev_rsi = rsi(closes[:-1], 14)
            if prev_rsi is not None and prev_rsi < 30:
                b += 2
                tags.append("RSI 과매도 탈출")
        elif rsi_val < 30:
            b += 1

    # RSI 상승 다이버전스 (+2)
    if _rsi_bullish_divergence(closes):
        b += 2
        tags.append("RSI 상승 다이버전스")

    # 스토캐스틱 과매도 탈출 (+2)
    sk, sd = stochastic(highs, lows, closes, 14, 3)
    signals.update({"stoch_k": sk, "stoch_d": sd})
    if sk is not None and sd is not None:
        if sk >= 20:
            pk, pd = stochastic(highs[:-1], lows[:-1], closes[:-1], 14, 3)
            if pk is not None and pk < 20:
                b += 2
                tags.append("스토캐스틱 과매도 탈출")
        elif sk < 20:
            b += 1

    # CCI 과매도 탈출 (+2)
    cci_val = cci(highs, lows, closes, 20)
    signals["cci"] = cci_val
    if cci_val is not None:
        if cci_val >= -100 and len(highs) >= 2:
            prev_cci = cci(highs[:-1], lows[:-1], closes[:-1], 20)
            if prev_cci is not None and prev_cci < -100:
                b += 2
                tags.append("CCI 과매도 탈출")

    # MFI 과매도 탈출 (+2)
    mfi_val = mfi(highs, lows, closes, volumes, 14)
    signals["mfi"] = mfi_val
    if mfi_val is not None:
        if mfi_val >= 20 and len(highs) >= 2:
            prev_mfi = mfi(highs[:-1], lows[:-1], closes[:-1], volumes[:-1], 14)
            if prev_mfi is not None and prev_mfi < 20:
                b += 2
                tags.append("MFI 과매도 탈출")
        elif mfi_val < 20:
            b += 1

    b = min(b, 10)

    # ── C. 변동성/가격패턴 (max 10) ──────────────────────────────────────────
    c = 0

    atr_val = atr(highs, lows, closes, 14)
    signals["atr"] = atr_val

    bb = bollinger(closes, 20, 2.0)
    if bb is not None:
        bbu, bbm, bbl = bb
        bandwidth = (bbu - bbl) / bbm * 100 if bbm != 0 else 0
        signals.update({"bb_upper": bbu, "bb_lower": bbl, "bb_bandwidth": round(bandwidth, 2)})
        # 볼린저 하단 근접 (+2)
        if cur <= bbl * 1.02:
            c += 2
            tags.append("볼린저 하단 근접")
        # 볼린저 스퀴즈 + 상단 돌파 (+2)
        if bandwidth < 10 and cur >= bbu:
            c += 2
            tags.append("볼린저 스퀴즈 상단돌파")
    else:
        signals.update({"bb_upper": None, "bb_lower": None, "bb_bandwidth": None})

    # 엔벨로프 하단지지 + 양봉 (+2)
    env = envelope(closes, 20, 0.05)
    if env is not None:
        env_u, _, env_l = env
        signals.update({"env_upper": env_u, "env_lower": env_l})
        if cur <= env_l * 1.01 and len(closes) >= 2 and closes[-1] > closes[-2]:
            c += 2
            tags.append("엔벨로프 하단지지")
    else:
        signals.update({"env_upper": None, "env_lower": None})

    # 피봇 S2 반등 (+2)
    if len(highs) >= 2:
        piv = pivot_point(highs[-2], lows[-2], closes[-2])
        signals["pivot_s2"] = piv["s2"]
        if piv["s2"] * 0.99 <= cur <= piv["s2"] * 1.05 and len(closes) >= 2 and closes[-1] > closes[-2]:
            c += 2
            tags.append("피봇 2차지지")
    else:
        signals["pivot_s2"] = None

    # 전고점 돌파 + 거래량 (+2)
    if len(highs) >= 22:
        recent_h = max(highs[-21:-1])
        vol_ma = sma(volumes, 20)
        if vol_ma and vol_ma > 0 and cur > recent_h and volumes[-1] > vol_ma * 1.5:
            c += 2
            tags.append("전고점 돌파")

    # 눌림목 반등 (+2)
    if ma20 is not None and len(closes) >= 10 and cur > ma20:
        uptrend = True
        for i in range(1, 6):
            if len(closes) < i + 20:
                uptrend = False
                break
            if (sma(closes[:-i], 5) or 0) <= (sma(closes[:-i], 20) or 0):
                uptrend = False
                break
        if uptrend and any(abs(l - ma20) / ma20 < 0.02 for l in lows[-5:]):
            c += 2
            tags.append("눌림목 반등")

    c = min(c, 10)

    # ── D. 거래량/매집 (max 10) ──────────────────────────────────────────────
    d = 0

    obv_s = obv_series(closes, volumes)
    signals["obv"] = obv_s[-1] if obv_s else None

    # OBV 상승추세 (+1, no tag)
    if len(obv_s) >= 10:
        if sum(obv_s[-5:]) / 5 > sum(obv_s[-10:]) / 10:
            d += 1

    # OBV 선행 돌파 (+2)
    if len(obv_s) >= 21 and len(highs) >= 21:
        obv_high = max(obv_s[-21:-1])
        price_high = max(highs[-21:-1])
        if obv_s[-1] > obv_high and cur <= price_high:
            d += 2
            tags.append("OBV 선행 돌파")
        elif obv_s[-1] > obv_high:
            d += 1

    # 거래량 급증 (+2)
    vol_ma20 = sma(volumes, 20)
    signals["volume_ma20"] = vol_ma20
    vol_ratio_val = None
    if vol_ma20 and vol_ma20 > 0:
        vol_ratio_val = round(volumes[-1] / vol_ma20, 2)
        signals["volume_ratio"] = vol_ratio_val
        if vol_ratio_val >= 2.0 and len(closes) >= 2 and closes[-1] > closes[-2]:
            d += 2
            tags.append("거래량 급증")
    else:
        signals["volume_ratio"] = None

    # VR 과매도 반등 (+2, no tag)
    vr = volume_ratio(closes, volumes, 20)
    signals["vr"] = round(vr, 1) if vr is not None else None
    if vr is not None and vr < 70:
        d += 2

    # Chaikin 0선 돌파 (+2)
    ch = chaikin_osc(highs, lows, closes, volumes)
    signals["chaikin_osc"] = ch
    if ch is not None and len(highs) >= 2:
        prev_ch = chaikin_osc(highs[:-1], lows[:-1], closes[:-1], volumes[:-1])
        if prev_ch is not None and prev_ch <= 0 and ch > 0:
            d += 2
            tags.append("Chaikin 0선돌파")
        elif ch > 0 and prev_ch is None:
            d += 1

    d = min(d, 10)

    # ── Final ─────────────────────────────────────────────────────────────────
    # Normalize 0-40 → 0-100
    total = a + b + c + d
    score = round(total * 2.5)
    strength = (
        "매우 강함" if score >= 75 else
        "강함"     if score >= 50 else
        "보통"     if score >= 25 else
        "약함"
    )

    return {
        "score": score,
        "tags": tags,
        "signals": signals,
        "score_detail": {"trend": a, "momentum": b, "volatility": c, "volume": d},
        "strength": strength,
    }
