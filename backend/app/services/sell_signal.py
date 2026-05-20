"""
매도 신호 분석 서비스.
기술적·기본적·자산관리 관점에서 매도 점수(0-100)와 매도 가격대를 계산한다.
"""

from app.services.technical import sma, rsi, stochastic, ema_series, _rma


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_series(records: list[dict]):
    closes, opens, highs, lows, volumes = [], [], [], [], []
    for r in records:
        try:
            closes.append(float(r.get("stck_clpr") or 0))
            opens.append(float(r.get("stck_oprc") or 0))
            highs.append(float(r.get("stck_hgpr") or 0))
            lows.append(float(r.get("stck_lwpr") or 0))
            volumes.append(float(r.get("acml_vol") or 0))
        except (ValueError, TypeError):
            continue
    return closes, opens, highs, lows, volumes


def _dead_cross(closes: list[float], fast: int, slow: int, lookback: int = 5) -> bool:
    """fast MA가 slow MA를 아래로 교차했는지 (최근 lookback 봉 이내)."""
    if len(closes) < slow + lookback:
        return False
    fast_now = sma(closes, fast)
    slow_now = sma(closes, slow)
    if fast_now is None or slow_now is None or fast_now >= slow_now:
        return False
    for i in range(1, lookback + 1):
        if len(closes) <= slow + i:
            break
        fp = sma(closes[:-i], fast)
        sp = sma(closes[:-i], slow)
        if fp is not None and sp is not None and fp >= sp:
            return True
    return False


def _macd_dead_cross(closes: list[float], lookback: int = 3) -> bool:
    """MACD가 시그널선을 아래로 교차했는지 (최근 lookback 봉 이내)."""
    fast, slow, sig = 12, 26, 9
    if len(closes) < slow + sig + lookback:
        return False

    def _compute(cl):
        fe = ema_series(cl, fast)
        se = ema_series(cl, slow)
        if not fe or not se:
            return None, None
        offset = slow - fast
        if len(fe) <= offset:
            return None, None
        ml = [f - s for f, s in zip(fe[offset:], se)]
        if len(ml) < sig:
            return None, None
        sl_ = ema_series(ml, sig)
        return (ml[-1], sl_[-1]) if sl_ else (None, None)

    mv, sv = _compute(closes)
    if mv is None or sv is None or mv >= sv:
        return False
    for i in range(1, lookback + 1):
        pv, ps = _compute(closes[:-i])
        if pv is not None and ps is not None and pv >= ps:
            return True
    return False


def _bearish_candle_volume(opens, closes, volumes, body_pct=2.0, vol_multiplier=1.5) -> bool:
    """최근 봉이 장대음봉이고 거래량이 평균 이상인지."""
    if len(closes) < 21 or not opens:
        return False
    last_open = opens[-1]
    last_close = closes[-1]
    if last_open == 0:
        return False
    body = (last_open - last_close) / last_open * 100
    avg_vol = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else None
    if avg_vol is None or avg_vol == 0:
        return False
    return body >= body_pct and volumes[-1] >= avg_vol * vol_multiplier


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------

def analyze_sell(
    records: list[dict],
    avg_price: int,
    current_price: int | None,
    per: float | None = None,
    pbr: float | None = None,
    eps: float | None = None,
    w52_high: int | None = None,
    portfolio_weight: float | None = None,
) -> dict:
    """
    Returns:
        sell_score  : int 0-100 (높을수록 매도 긴급)
        grade       : str "관망" | "주의" | "매도 검토" | "즉시 매도"
        signals     : list[{category, name, description, pts}]
        sell_levels : dict  — 기준 가격대
    """
    signals: list[dict] = []
    total_pts = 0

    def add(category: str, name: str, description: str, pts: int):
        nonlocal total_pts
        signals.append({"category": category, "name": name, "description": description, "pts": pts})
        total_pts += pts

    closes, opens, highs, lows, volumes = _extract_series(records)
    cp = current_price or (int(closes[-1]) if closes else None)

    # ------------------------------------------------------------------
    # 1. 기술적 신호
    # ------------------------------------------------------------------
    if len(closes) >= 25:

        # 1-a. 데드크로스
        if _dead_cross(closes, 5, 20, lookback=3):
            add("기술적", "MA5/20 데드크로스",
                "단기(5일) 이동평균이 중기(20일)를 하향 돌파했습니다.", 20)

        if _dead_cross(closes, 20, 60, lookback=5) and len(closes) >= 65:
            add("기술적", "MA20/60 데드크로스",
                "중기(20일) 이동평균이 장기(60일)를 하향 돌파했습니다.", 25)

        # 1-b. RSI 과매수
        rsi_val = rsi(closes, 14)
        if rsi_val is not None:
            if rsi_val > 80:
                add("기술적", "RSI 극과매수",
                    f"RSI {rsi_val:.1f} — 80 초과 구간으로 단기 고점 신호입니다.", 15)
            elif rsi_val > 70:
                add("기술적", "RSI 과매수",
                    f"RSI {rsi_val:.1f} — 70 초과 구간으로 분할 매도를 검토하세요.", 8)

        # 1-c. 스토캐스틱 과매수 데드크로스
        sk, sd = stochastic(highs, lows, closes, 14, 3)
        if sk is not None and sd is not None and sk > 70 and sk < sd:
            add("기술적", "스토캐스틱 과매수 데드크로스",
                f"%K({sk:.1f}) < %D({sd:.1f}) 상태로 과매수 구간에서 시그널 하향 교차했습니다.", 10)

        # 1-d. 장대음봉 + 대량 거래량
        if _bearish_candle_volume(opens, closes, volumes):
            add("기술적", "장대음봉 + 대량 거래",
                "고점 부근에서 대량 거래를 동반한 장대음봉 — 세력 이탈 가능성이 있습니다.", 12)

        # 1-e. 주가 위치
        ma20 = sma(closes, 20)
        ma60 = sma(closes, 60) if len(closes) >= 60 else None
        if cp and ma20 and cp < ma20:
            if ma60 and cp < ma60:
                add("기술적", "주가 MA60 하회",
                    f"현재가({cp:,})가 60일 이평선({int(ma60):,}) 아래입니다.", 8)
            else:
                add("기술적", "주가 MA20 하회",
                    f"현재가({cp:,})가 20일 이평선({int(ma20):,}) 아래입니다.", 5)

        # 1-f. MACD 데드크로스
        if _macd_dead_cross(closes):
            add("기술적", "MACD 데드크로스",
                "MACD선이 시그널선을 하향 돌파했습니다.", 10)

    # ------------------------------------------------------------------
    # 2. 기본적 신호
    # ------------------------------------------------------------------
    if per is not None and per > 0:
        if per > 80:
            add("기본적", "PER 극과열",
                f"PER {per:.1f}배 — 밸류에이션이 극도로 높습니다.", 15)
        elif per > 50:
            add("기본적", "PER 과열",
                f"PER {per:.1f}배 — 고평가 구간입니다.", 10)
        elif per > 30:
            add("기본적", "PER 주의",
                f"PER {per:.1f}배 — 평균 대비 높은 편입니다.", 5)

    if pbr is not None and pbr > 0:
        if pbr > 5:
            add("기본적", "PBR 과열",
                f"PBR {pbr:.2f}배 — 장부가 대비 고평가입니다.", 10)
        elif pbr > 3:
            add("기본적", "PBR 주의",
                f"PBR {pbr:.2f}배 — 장부가 대비 높은 편입니다.", 5)

    # ------------------------------------------------------------------
    # 3. 자산 관리 신호
    # ------------------------------------------------------------------
    if cp:
        gain_pct = (cp - avg_price) / avg_price * 100

        # 손절 구간
        if cp < avg_price * 0.90:
            add("자산관리", "손절 -10% 이탈",
                f"현재가({cp:,})가 매수가({avg_price:,}) 대비 -10% 이하입니다. 즉시 손절을 고려하세요.", 25)
        elif cp < avg_price * 0.95:
            add("자산관리", "손절 -5% 근접",
                f"현재가({cp:,})가 매수가({avg_price:,}) 대비 -5% 이하입니다.", 15)

        # 고수익 트레일링 스탑 경고
        if gain_pct > 20 and closes:
            recent_high = max(closes[-60:] if len(closes) >= 60 else closes)
            trailing_7 = recent_high * 0.93
            if cp < trailing_7:
                add("자산관리", "트레일링 스탑 -7% 이탈",
                    f"고점({int(recent_high):,}) 대비 7% 이상 하락 — 수익 보존을 위한 매도를 검토하세요.", 12)

    # 포트폴리오 비중
    if portfolio_weight is not None:
        if portfolio_weight > 35:
            add("자산관리", "포트폴리오 과집중",
                f"현재 비중 {portfolio_weight:.1f}% — 35% 초과로 리밸런싱을 고려하세요.", 12)
        elif portfolio_weight > 25:
            add("자산관리", "포트폴리오 비중 주의",
                f"현재 비중 {portfolio_weight:.1f}% — 25% 초과입니다.", 8)

    # ------------------------------------------------------------------
    # 점수 산정 및 등급
    # ------------------------------------------------------------------
    sell_score = min(100, total_pts)

    if sell_score <= 20:
        grade = "관망"
    elif sell_score <= 40:
        grade = "주의"
    elif sell_score <= 65:
        grade = "매도 검토"
    else:
        grade = "즉시 매도"

    return {
        "sell_score": sell_score,
        "grade": grade,
        "signals": signals,
        "sell_levels": _sell_levels(avg_price, eps, closes, cp, w52_high),
    }


def _sell_levels(
    avg_price: int,
    eps: float | None,
    closes: list[float],
    current_price: int | None,
    w52_high: int | None,
) -> dict:
    levels: dict = {
        "stop_loss_5":  int(avg_price * 0.95),
        "stop_loss_10": int(avg_price * 0.90),
        "stop_loss_15": int(avg_price * 0.85),
    }

    # 트레일링 스탑 기준: 최근 60봉 고점
    if closes:
        window = closes[-60:] if len(closes) >= 60 else closes
        recent_high = max(window)
        if current_price:
            recent_high = max(recent_high, current_price)
        levels["trailing_high_ref"] = int(recent_high)
        levels["trailing_stop_7"]   = int(recent_high * 0.93)
        levels["trailing_stop_10"]  = int(recent_high * 0.90)

    # EPS 기반 목표가
    if eps and eps > 0:
        levels["target_per15"] = int(eps * 15)
        levels["target_per20"] = int(eps * 20)
        levels["target_per25"] = int(eps * 25)

    if w52_high:
        levels["w52_high"] = w52_high

    return levels
