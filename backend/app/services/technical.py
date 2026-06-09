"""
Technical analysis dual-engine scoring module for MPM recommendation engine.
All indicator functions operate on chronologically sorted data (oldest first).

Stage 1 — Hard Filter
  MA20 daily volume ≥ MIN_VOL_MA20. Fails → score=0 immediately.

Stage 2 — Dual Engine Scoring (each 0-100)
  Engine A – Trend Following (max 100)
    골든크로스 (15) · ADX/DMI 상승추세 (15) · 일목 구름대 돌파 (15)
    볼린저 스퀴즈 상단돌파 (15) · 전고점 돌파+거래량 (15)
    OBV 선행 돌파 (15) · 거래량 급증 (10)
    Hard Veto: RSI ≥ 80 → 0 (극과열, 진입 금지)
    RSI 70 최초 돌파: +5 (모멘텀 가산)
    Soft Veto: RSI ≥ 70 지속 → -10
    BEAR 시장: 즉시 0 (가짜 돌파 위험)

  Engine B – Mean Reversion (max 100)
    Pre-filter: 거래대금 50억 미만 → 0 (유동성 부족)
    Pre-filter: MA60 우하향 중 → 0 (칼날 잡기 방지)
    B1 (disparity < 99): 이격도(15) + 과매도그룹(25) + 수요밴드(35) / 75 * 100
    B2 (disparity ≥ 99): 과매도그룹(25) + 수요밴드(35) + 눌림목(25) / 85 * 100

  Final score = max(engine_a_score, engine_b_score).
  Winning engine sets tags.
"""

import math

# ── Constants ──────────────────────────────────────────────────────────────────
MIN_VOL_MA20 = 100_000   # Hard filter: minimum MA20 daily volume (shares)


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
    """Parabolic SAR. Returns (sar_value, is_bullish)."""
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


def fibonacci_support(
    highs: list[float], lows: list[float], closes: list[float],
    n: int = 3, tolerance: float = 0.02
) -> dict:
    """
    Fibonacci retracement support detection.
    Returns {"level", "ratio", "near": bool, "reason"}.
    """
    def _no(reason: str) -> dict:
        return {"level": None, "ratio": None, "near": False, "reason": reason}

    min_len = 2 * n + 5
    if len(closes) < min_len:
        return _no("데이터 부족")

    search_end = len(closes) - n
    swing_highs: list[tuple[int, float]] = []
    swing_lows: list[tuple[int, float]] = []
    for i in range(n, search_end):
        if highs[i] == max(highs[i - n: i + n + 1]):
            swing_highs.append((i, highs[i]))
        if lows[i] == min(lows[i - n: i + n + 1]):
            swing_lows.append((i, lows[i]))

    if not swing_highs or not swing_lows:
        return _no("스윙 감지 불가")

    sh_idx = sh_price = sl_idx = sl_price = None
    for _sh_idx, _sh_price in reversed(swing_highs):
        preceding = [(i, p) for i, p in swing_lows if i < _sh_idx]
        if not preceding:
            continue
        _sl_idx, _sl_price = preceding[-1]
        _range = _sh_price - _sl_price
        if _range > 0 and _range / _sl_price >= 0.03:
            sh_idx, sh_price = _sh_idx, _sh_price
            sl_idx, sl_price = _sl_idx, _sl_price
            break

    if sh_idx is None:
        return _no("유효 스윙 없음")

    swing_range = sh_price - sl_price
    cur = closes[-1]
    l382 = sh_price - 0.382 * swing_range
    l500 = sh_price - 0.500 * swing_range
    l618 = sh_price - 0.618 * swing_range

    for ratio, level in [(0.382, l382), (0.500, l500), (0.618, l618)]:
        if abs(cur - level) / level <= tolerance:
            return {"level": round(level, 0), "ratio": ratio, "near": True, "reason": None}

    def _fmt(v: float) -> str:
        return f"{int(round(v)):,}"

    if cur > l382:
        return _no(f"되돌림 전 · 38.2%={_fmt(l382)}")
    elif cur < l618:
        return _no(f"61.8% 이탈 · 기준={_fmt(l618)}")
    elif cur > l500:
        return _no(f"38.2%~50% 구간 ({_fmt(l382)}~{_fmt(l500)})")
    else:
        return _no(f"50%~61.8% 구간 ({_fmt(l500)}~{_fmt(l618)})")


def volume_ratio(closes: list[float], volumes: list[float], period: int = 20) -> float | None:
    """VR = (up_vol + 0.5*flat_vol) / (down_vol + 0.5*flat_vol) × 100."""
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


# ── Engine A: Trend Following (0-100) ─────────────────────────────────────────

def _engine_a(
    closes: list[float], highs: list[float], lows: list[float], volumes: list[float],
    cur: float, ma5: float | None, ma20: float | None, ma60: float | None,
    rsi_val: float | None, vol_ma20: float, cloud_position: str,
    market_regime: str = "BULL",
    prev_rsi: float | None = None,
) -> tuple[int, list[str]]:
    # 하락장에서 추세 돌파는 가짜 돌파 확률이 높으므로 즉시 0점
    if market_regime == "BEAR":
        return 0, []

    score = 0
    tags: list[str] = []

    # 1. 골든크로스 (max 15)
    if ma5 is not None and ma20 is not None:
        full_aligned = ma60 is not None and ma5 > ma20 > ma60
        crossed = False
        for offset in range(1, 4):
            if len(closes) >= offset + 20:
                pm5 = sma(closes[:-offset], 5)
                pm20 = sma(closes[:-offset], 20)
                if pm5 is not None and pm20 is not None and pm5 <= pm20 and ma5 > ma20:
                    crossed = True
                    break
        if full_aligned or crossed:
            score += 15
            tags.append("골든크로스")
        elif ma5 > ma20:
            score += 8

    # 2. 강한 상승추세 ADX/DMI (max 15)
    plus_di, minus_di, adx = dmi(highs, lows, closes, 14)
    if adx is not None and plus_di is not None and minus_di is not None and plus_di > minus_di:
        if adx >= 25:
            score += 15
            tags.append("강한 상승추세")
        elif adx >= 20:
            score += 10
            tags.append("강한 상승추세")

    # 3. 일목 구름대 돌파 (max 15)
    if cloud_position == "above_cloud":
        score += 15
        tags.append("일목 구름대 돌파")
    elif cloud_position == "in_cloud":
        score += 5

    # 4. 볼린저 스퀴즈 상단돌파 (max 15)
    bb = bollinger(closes, 20, 2.0)
    if bb is not None:
        bbu, bbm, _ = bb
        bandwidth = (bbu - bb[2]) / bbm * 100 if bbm != 0 else 0
        if bandwidth < 10 and cur >= bbu:
            score += 15
            tags.append("볼린저 스퀴즈 상단돌파")
        elif bandwidth < 10 and cur > bbm:
            score += 6

    # 5. 전고점 돌파 + 거래량 (max 15)
    if len(highs) >= 22 and vol_ma20 > 0:
        recent_h = max(highs[-21:-1])
        if cur > recent_h:
            vol_ratio_val = volumes[-1] / vol_ma20 if vol_ma20 > 0 else 0
            score += 15 if vol_ratio_val >= 1.5 else 8
            tags.append("전고점 돌파")

    # 6. OBV 선행 돌파 (max 15)
    obv_s = obv_series(closes, volumes)
    if len(obv_s) >= 21 and len(highs) >= 21:
        obv_high = max(obv_s[-21:-1])
        price_high = max(highs[-21:-1])
        if obv_s[-1] > obv_high:
            if cur <= price_high:   # OBV leads price — strongest signal
                score += 15
                tags.append("OBV 선행 돌파")
            else:
                score += 8

    # 7. 거래량 급증 (max 10)
    if vol_ma20 > 0 and len(closes) >= 2 and closes[-1] > closes[-2]:
        vr = volumes[-1] / vol_ma20
        if vr >= 3.0:
            score += 10
            tags.append("거래량 급증")
        elif vr >= 2.0:
            score += 7
            tags.append("거래량 급증")
        elif vr >= 1.5:
            score += 3

    # RSI 과열 처리 (3단계)
    if rsi_val is not None:
        if rsi_val >= 80:
            return 0, []  # Hard Veto — 극과열 구간, 진입 금지
        elif rsi_val >= 70 and prev_rsi is not None and prev_rsi < 70:
            score += 5   # 최초 70 돌파 = 강한 모멘텀 가산
        elif rsi_val >= 70:
            score = max(0, score - 10)  # 고점 지속 = Soft Veto

    return min(100, score), tags


# ── Engine B: Mean Reversion (0-100) ──────────────────────────────────────────

def _engine_b(
    closes: list[float], highs: list[float], lows: list[float], volumes: list[float],
    cur: float, ma5: float | None, ma20: float | None,
    rsi_val: float | None,
    transaction_amount: float = 0,
    ma60: float | None = None,
    ma60_prev: float | None = None,
) -> tuple[int, list[str]]:
    # Pre-filter 1: 일 거래대금 50억 미만 — 유동성 부족 종목
    if transaction_amount < 5_000_000_000:
        return 0, []

    # Pre-filter 2: MA60 우하향 중 — 칼날 잡기 방지
    if ma60 is not None and ma60_prev is not None and ma60 < ma60_prev:
        return 0, []

    tags: list[str] = []
    bullish = len(closes) >= 2 and closes[-1] > closes[-2]
    disparity = cur / ma20 * 100 if (ma20 is not None and ma20 > 0) else 100.0

    # ── 공통 지표 (B1/B2 모두 사용) ──────────────────────────────────────────

    # 과매도 그룹: RSI / Stoch / CCI / MFI (max 25)
    oversold_signals: list[str] = []
    if rsi_val is not None and rsi_val < 35:
        oversold_signals.append("RSI")
    sk, _ = stochastic(highs, lows, closes, 14, 3)
    if sk is not None and sk < 25:
        oversold_signals.append("Stoch")
    cci_val = cci(highs, lows, closes, 20)
    if cci_val is not None and cci_val < -80:
        oversold_signals.append("CCI")
    mfi_val = mfi(highs, lows, closes, volumes, 14)
    if mfi_val is not None and mfi_val < 25:
        oversold_signals.append("MFI")

    n_over = len(oversold_signals)
    if n_over >= 3:
        oversold_score = 25
        tags.append(f"과매도 집중({'+'.join(oversold_signals)})")
    elif n_over == 2:
        oversold_score = 20
        tags.append(f"과매도 집중({'+'.join(oversold_signals)})")
    elif n_over == 1:
        oversold_score = 10
        tags.append(f"{oversold_signals[0]} 과매도")
    else:
        oversold_score = 0

    # 수요밴드 통합: Bollinger / Envelope / Pivot S2 / Fibonacci (max 35)
    support_labels: list[str] = []
    bb = bollinger(closes, 20, 2.0)
    if bb is not None and cur <= bb[2] * 1.02:
        support_labels.append("볼린저하단")
    env = envelope(closes, 20, 0.05)
    if env is not None and cur <= env[2] * 1.01:
        support_labels.append("엔벨로프하단")
    if len(highs) >= 2:
        piv = pivot_point(highs[-2], lows[-2], closes[-2])
        if piv["s2"] * 0.99 <= cur <= piv["s2"] * 1.05:
            support_labels.append("피봇S2")
    fib = fibonacci_support(highs, lows, closes)
    if fib["near"]:
        support_labels.append(f"피보나치{round((fib['ratio'] or 0) * 100, 0):.0f}%")

    n_sup = len(support_labels)
    if n_sup >= 2:
        demand_band_score = 35 if bullish else 20
        tags.append(f"수요밴드({'+'.join(support_labels[:2])})")
    elif n_sup == 1:
        demand_band_score = 20 if bullish else 8
        tags.append(support_labels[0])
    else:
        demand_band_score = 0

    # ── B1 / B2 분기 처리 ────────────────────────────────────────────────────

    if disparity < 99:
        # B1: 낙폭과대 V자 반등형 (이격도 + 과매도 + 수요밴드, 만점 75)
        if disparity < 93:
            disp_score = 15
            tags.append("이격도 저점")
        elif disparity < 95:
            disp_score = 12
            tags.append("이격도 저점")
        elif disparity < 97:
            disp_score = 8
            tags.append("이격도 저점")
        else:
            disp_score = 3

        raw_score = disp_score + oversold_score + demand_band_score
        final_score = int(raw_score / 75 * 100)
    else:
        # B2: 정배열 눌림목형 (과매도 + 수요밴드 + 눌림목, 만점 85)
        nulim_score = 0
        if (ma5 is not None and ma20 is not None and ma5 > ma20 and cur > ma20
                and lows and any(abs(l - ma20) / ma20 < 0.02 for l in lows[-5:])):
            if bullish:
                nulim_score = 25
                tags.append("눌림목 반등")
            else:
                nulim_score = 12
                tags.append("눌림목 근접")

        raw_score = oversold_score + demand_band_score + nulim_score
        final_score = int(raw_score / 85 * 100)

    return min(100, final_score), tags


# ── Main scoring function ──────────────────────────────────────────────────────

def analyze(
    records: list[dict],
    cloud_position: str = "unknown",
    market_regime: str = "BULL",
) -> dict:
    """
    Dual-engine technical analysis scoring.

    Args:
        records: OHLCV dicts sorted oldest-first (keys: stck_hgpr, stck_lwpr, stck_clpr, acml_vol).
        cloud_position: "above_cloud" | "in_cloud" | "below_cloud" | "unknown".
        market_regime: "BULL" | "BEAR" — KOSPI MA20 기반 시장 국면, Engine A에 전달.
    """
    EMPTY: dict = {
        "score": 0, "tags": [], "signals": {},
        "engine": None, "engine_a_score": 0, "engine_b_score": 0,
        "score_detail": {"engine_a": 0, "engine_b": 0},
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

    cur = closes[-1]

    # ── Stage 1: Hard Filter ──────────────────────────────────────────────────
    vol_ma20 = sma(volumes, 20)
    if vol_ma20 is None or vol_ma20 < MIN_VOL_MA20:
        return {**EMPTY, "filter_failed": "low_volume"}

    # ── Pre-compute shared indicators ─────────────────────────────────────────
    ma5  = sma(closes, 5)
    ma20 = sma(closes, 20)
    ma60 = sma(closes, 60) if len(closes) >= 60 else None
    rsi_val = rsi(closes, 14)
    atr_val = atr(highs, lows, closes, 14)

    # Engine A: 직전 봉 RSI (최초 70 돌파 감지용)
    prev_rsi = rsi(closes[:-1], 14) if len(closes) >= 16 else None

    # Engine B: MA60 기울기 (5봉 전 대비 하향 여부 판단)
    ma60_prev = sma(closes[:-5], 60) if len(closes) >= 65 else None

    # Engine B: 당일 거래대금 추정 (종가 × 거래량)
    transaction_amount = closes[-1] * volumes[-1]

    # ── Stage 2: Dual Engine ──────────────────────────────────────────────────
    score_a, tags_a = _engine_a(
        closes, highs, lows, volumes, cur,
        ma5, ma20, ma60, rsi_val, vol_ma20, cloud_position,
        market_regime=market_regime,
        prev_rsi=prev_rsi,
    )
    score_b, tags_b = _engine_b(
        closes, highs, lows, volumes, cur,
        ma5, ma20, rsi_val,
        transaction_amount=transaction_amount,
        ma60=ma60,
        ma60_prev=ma60_prev,
    )

    if score_a >= score_b:
        engine, score, tags = "A", score_a, tags_a
    else:
        engine, score, tags = "B", score_b, tags_b

    strength = (
        "매우 강함" if score >= 75 else
        "강함"     if score >= 50 else
        "보통"     if score >= 25 else
        "약함"
    )

    # ── Display signals: all indicators for detail page ────────────────────────
    macd_res = _macd_series(closes)
    macd_val = macd_res[0][-1] if macd_res and macd_res[0] else None
    macd_sig = macd_res[1][-1] if macd_res and macd_res[1] else None

    sk, sd = stochastic(highs, lows, closes, 14, 3)
    cci_v   = cci(highs, lows, closes, 20)
    mfi_v   = mfi(highs, lows, closes, volumes, 14)
    plus_di, minus_di, adx = dmi(highs, lows, closes, 14)
    obv_s   = obv_series(closes, volumes)
    env     = envelope(closes, 20, 0.05)
    sar_v, _ = parabolic_sar(highs, lows)
    fib     = fibonacci_support(highs, lows, closes)
    vr_v    = volume_ratio(closes, volumes, 20)
    ch_v    = chaikin_osc(highs, lows, closes, volumes)
    bb      = bollinger(closes, 20, 2.0)

    if bb is not None:
        bbu, bbm, bbl = bb
        bw = round((bbu - bbl) / bbm * 100, 2) if bbm else None
    else:
        bbu = bbm = bbl = bw = None

    piv_s2    = pivot_point(highs[-2], lows[-2], closes[-2])["s2"] if len(highs) >= 2 else None
    disparity = round(cur / ma20 * 100, 2) if ma20 else None
    vol_ratio_v = round(volumes[-1] / vol_ma20, 2) if vol_ma20 > 0 else None

    signals = {
        "ma5": ma5, "ma20": ma20, "ma60": ma60,
        "macd": round(macd_val) if macd_val is not None else None,
        "macd_signal": round(macd_sig) if macd_sig is not None else None,
        "rsi": round(rsi_val, 1) if rsi_val is not None else None,
        "stoch_k": round(sk, 1) if sk is not None else None,
        "stoch_d": round(sd, 1) if sd is not None else None,
        "bb_upper": round(bbu) if bbu is not None else None,
        "bb_lower": round(bbl) if bbl is not None else None,
        "bb_bandwidth": bw,
        "disparity": disparity,
        "adx": round(adx, 1) if adx is not None else None,
        "plus_di": round(plus_di, 1) if plus_di is not None else None,
        "minus_di": round(minus_di, 1) if minus_di is not None else None,
        "cci": round(cci_v, 1) if cci_v is not None else None,
        "mfi": round(mfi_v, 1) if mfi_v is not None else None,
        "atr": round(atr_val) if atr_val is not None else None,
        "obv": obv_s[-1] if obv_s else None,
        "volume_ma20": round(vol_ma20),
        "volume_ratio": vol_ratio_v,
        "vr": round(vr_v, 1) if vr_v is not None else None,
        "chaikin_osc": round(ch_v) if ch_v is not None else None,
        "parabolic_sar": round(sar_v) if sar_v is not None else None,
        "env_upper": round(env[0]) if env is not None else None,
        "env_lower": round(env[2]) if env is not None else None,
        "pivot_s2": round(piv_s2) if piv_s2 is not None else None,
        "fib_level": fib["level"],
        "fib_ratio": fib["ratio"],
        "fib_reason": fib["reason"],
        "cloud_position": cloud_position,
    }

    return {
        "score": score,
        "tags": tags,
        "signals": signals,
        "engine": engine,
        "engine_a_score": score_a,
        "engine_b_score": score_b,
        "score_detail": {"engine_a": score_a, "engine_b": score_b},
        "strength": strength,
    }
