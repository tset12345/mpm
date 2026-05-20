"""
기대 수익률 분석 모듈.
펀더멘탈 목표가 / 확률 기반 기댓값 / 손익비를 계산한다.
"""


def compute(
    current_price: float,
    eps: float | None,
    bps: float | None,
    roe: float | None,
    stop_loss: float | None = None,
    target_per: float = 15.0,
    coe: float = 0.08,
) -> dict:
    """
    Args:
        current_price : 현재 주가
        eps           : Trailing EPS (Forward EPS 미제공 시 대체 사용)
        bps           : 주당 순자산
        roe           : ROE (%, e.g. 12.5)
        stop_loss     : 기술적 손절가 (None이면 현재가 -10% 자동 설정)
        target_per    : 목표 PER (기본 15)
        coe           : 요구수익률 (기본 0.08 = 8%)
    """
    result: dict = {
        "current_price": current_price,
        "target_per": target_per,
        "coe": coe * 100,               # % 표시용
        "target_price_per": None,        # A. Target PER 방식
        "target_price_pbr": None,        # B. PBR-ROE 방식
        "target_price": None,            # 최종 펀더멘탈 목표가
        "target_upside": None,
        "stop_loss": None,
        "stop_loss_rate": None,
        "expected_value": None,
        "risk_reward": None,
        "verdict": None,
        "verdict_reason": None,
    }

    # ── 손절가 ────────────────────────────────────────────────────────────────
    sl = stop_loss if (stop_loss and stop_loss < current_price) else current_price * 0.90
    result["stop_loss"] = round(sl)
    result["stop_loss_rate"] = round((sl - current_price) / current_price * 100, 2)

    # ── A. Target PER 방식 ────────────────────────────────────────────────────
    tp_per: float | None = None
    if eps and eps > 0:
        tp_per = eps * target_per
        result["target_price_per"] = round(tp_per)

    # ── B. PBR-ROE 방식 ───────────────────────────────────────────────────────
    tp_pbr: float | None = None
    if bps and bps > 0 and roe and roe > 0 and coe > 0:
        fair_pbr = (roe / 100) / coe      # ROE는 % → 소수 변환
        tp_pbr = bps * fair_pbr
        result["target_price_pbr"] = round(tp_pbr)

    # ── 최종 펀더멘탈 목표가 ──────────────────────────────────────────────────
    valid = [v for v in [tp_per, tp_pbr] if v is not None]
    if not valid:
        return result                      # 계산 불가 (EPS, BPS, ROE 모두 없음)

    target = sum(valid) / len(valid)
    result["target_price"] = round(target)
    upside = (target - current_price) / current_price * 100
    result["target_upside"] = round(upside, 2)

    # 목표가가 현재가 이하이면 의미 없음
    if target <= current_price:
        result["verdict"] = "진입 보류"
        result["verdict_reason"] = f"펀더멘탈 목표가({round(target):,}원)가 현재가 이하"
        return result

    # ── B. 확률 기반 기댓값 ───────────────────────────────────────────────────
    upside_rate = upside / 100           # 소수
    downside_rate = result["stop_loss_rate"] / 100
    ev = 0.6 * upside_rate + 0.4 * downside_rate
    result["expected_value"] = round(ev * 100, 2)   # %

    # ── C. 손익비 ─────────────────────────────────────────────────────────────
    risk = current_price - sl
    reward = target - current_price
    if risk > 0:
        rr = reward / risk
        result["risk_reward"] = round(rr, 2)
    else:
        rr = None

    # ── 최종 진입 판단 ────────────────────────────────────────────────────────
    if rr is not None and rr >= 2.0 and ev > 0:
        result["verdict"] = "진입 승인"
        result["verdict_reason"] = (
            f"손익비 {rr:.1f}:1로 진입 기준(2:1) 충족, "
            f"확률 기댓값 +{ev*100:.1f}%"
        )
    else:
        reasons = []
        if rr is not None and rr < 2.0:
            reasons.append(f"손익비 {rr:.1f}:1 (기준 미달)")
        if ev <= 0:
            reasons.append(f"확률 기댓값 {ev*100:.1f}% (음수)")
        result["verdict"] = "진입 보류"
        result["verdict_reason"] = ", ".join(reasons) if reasons else "조건 미충족"

    return result
