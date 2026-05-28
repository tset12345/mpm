"""
퀀트형 기대 수익률 분석 (QuantStrategy).

알고리즘 (외부 ML 라이브러리 없이 순수 수학/pandas 연산):
  1. 모멘텀 요인 (40점):
       - MA20 이격도: (현재가 / MA20) 비율
       - RSI(14)
  2. 가치 요인 (40점):
       - PER 수준 (섹터 상대 절대 기준)
       - PBR 수준
  3. 변동성 요인 (20점):
       - 20일 일별 수익률 표준편차 → 연환산

최종 통합 퀀트 점수(0~100)와 단기 방향성 힌트를 반환한다.

입력(data dict) 예시:
  {
    "current_price": 55000,
    "per": 12.5,       # None 허용
    "pbr": 0.8,        # None 허용
    "ohlcv": [         # 최근 60~90일, 오래된 순 정렬
      {"close": 54000, "high": 55000, "low": 53500, "open": 53800, "volume": 15000000},
      ...
    ],
  }
"""

from __future__ import annotations

import math
from typing import Optional

from .base import BaseStrategy, StrategyValidationError


class QuantStrategy(BaseStrategy):
    REQUIRED_KEYS = ["current_price", "ohlcv"]

    # 요인별 가중치 (합 = 100)
    _W_MOMENTUM = 40
    _W_VALUE = 40
    _W_VOLATILITY = 20

    # ── 공개 인터페이스 ────────────────────────────────────────────────────────

    def calculate_expected_return(self, data: dict) -> dict:
        """퀀트 통합 점수와 방향성 힌트를 계산한다."""
        self.validate(data)

        current_price: float = float(data["current_price"])
        per: Optional[float] = data.get("per")
        pbr: Optional[float] = data.get("pbr")
        ohlcv: list[dict] = data["ohlcv"]

        if len(ohlcv) < 20:
            raise StrategyValidationError(
                f"OHLCV 데이터가 최소 20봉 필요합니다. (현재 {len(ohlcv)}봉)"
            )

        import pandas as pd
        df = pd.DataFrame(ohlcv)
        closes = df["close"].astype(float)

        # ── 요인 계산 ─────────────────────────────────────────────────────────
        mom_score, mom_detail = self._momentum_score(closes, current_price)
        val_score, val_detail = self._value_score(per, pbr)
        vol_score, vol_detail = self._volatility_score(closes)

        # ── 통합 점수 ─────────────────────────────────────────────────────────
        quant_score = mom_score + val_score + vol_score

        direction_hint = self._direction_hint(quant_score, mom_detail, val_detail)
        verdict, verdict_reason = self._verdict(quant_score, mom_detail, val_detail, vol_detail)

        return {
            "quant_score": quant_score,
            "direction_hint": direction_hint,
            "factor_scores": {
                "momentum": {"score": mom_score, "max": self._W_MOMENTUM, **mom_detail},
                "value":    {"score": val_score, "max": self._W_VALUE,    **val_detail},
                "volatility": {"score": vol_score, "max": self._W_VOLATILITY, **vol_detail},
            },
            "verdict": verdict,
            "verdict_reason": verdict_reason,
        }

    # ── 모멘텀 요인 (0 ~ 40점) ────────────────────────────────────────────────

    def _momentum_score(
        self, closes: pd.Series, current_price: float
    ) -> tuple[int, dict]:
        detail: dict = {}

        # MA20 이격도
        ma20 = float(closes.rolling(20).mean().iloc[-1])
        deviation = current_price / ma20
        detail["ma20"] = round(ma20, 2)
        detail["ma20_deviation"] = round(deviation, 4)

        if deviation < 0.93:        # -7% 이하 — 과매도
            ma_pts = 20
        elif deviation < 0.97:      # -3~7% — 저평가 영역
            ma_pts = 16
        elif deviation < 1.03:      # ±3% — 중립
            ma_pts = 12
        elif deviation < 1.07:      # +3~7% — 다소 과매수
            ma_pts = 6
        else:                       # +7% 초과 — 과매수
            ma_pts = 0

        # RSI(14) — pandas rolling으로 계산
        rsi_val = self._rsi_pandas(closes, 14)
        detail["rsi14"] = round(rsi_val, 1) if rsi_val is not None else None

        if rsi_val is None:
            rsi_pts = 10   # 중립
        elif rsi_val < 30:          # 과매도 — 반등 기대
            rsi_pts = 18
        elif rsi_val < 50:          # 회복 구간
            rsi_pts = 20
        elif rsi_val < 60:          # 적정
            rsi_pts = 15
        elif rsi_val < 70:          # 다소 높음
            rsi_pts = 8
        else:                       # 과매수
            rsi_pts = 0

        score = min(self._W_MOMENTUM, ma_pts + rsi_pts)
        detail["ma20_pts"] = ma_pts
        detail["rsi_pts"] = rsi_pts
        return score, detail

    # ── 가치 요인 (0 ~ 40점) ──────────────────────────────────────────────────

    def _value_score(
        self, per: Optional[float], pbr: Optional[float]
    ) -> tuple[int, dict]:
        detail: dict = {"per": per, "pbr": pbr}

        # PER 점수 (20점)
        if per is None or per <= 0:
            per_pts = 10   # 데이터 없음: 중립
        elif per < 8:
            per_pts = 20
        elif per < 12:
            per_pts = 17
        elif per < 15:
            per_pts = 14
        elif per < 20:
            per_pts = 10
        elif per < 30:
            per_pts = 5
        else:
            per_pts = 0

        # PBR 점수 (20점)
        if pbr is None or pbr <= 0:
            pbr_pts = 10   # 중립
        elif pbr < 0.5:
            pbr_pts = 20
        elif pbr < 1.0:
            pbr_pts = 17
        elif pbr < 1.5:
            pbr_pts = 13
        elif pbr < 2.5:
            pbr_pts = 8
        elif pbr < 4.0:
            pbr_pts = 3
        else:
            pbr_pts = 0

        score = min(self._W_VALUE, per_pts + pbr_pts)
        detail["per_pts"] = per_pts
        detail["pbr_pts"] = pbr_pts
        return score, detail

    # ── 변동성 요인 (0 ~ 20점) ────────────────────────────────────────────────

    def _volatility_score(self, closes: pd.Series) -> tuple[int, dict]:
        detail: dict = {}

        # 20일 일별 로그 수익률 표준편차 → 연환산 변동성
        log_returns = (closes / closes.shift(1)).apply(math.log).dropna()
        window = log_returns.tail(20)
        if len(window) < 5:
            return 10, {"annualized_vol": None, "vol_pts": 10}

        daily_std = float(window.std())
        ann_vol = daily_std * math.sqrt(252) * 100   # % 단위
        detail["annualized_vol"] = round(ann_vol, 2)

        if ann_vol < 15:
            pts = 20
        elif ann_vol < 25:
            pts = 15
        elif ann_vol < 35:
            pts = 10
        elif ann_vol < 50:
            pts = 5
        else:
            pts = 0

        detail["vol_pts"] = pts
        return pts, detail

    # ── 방향성 힌트 & 판단 ────────────────────────────────────────────────────

    @staticmethod
    def _direction_hint(score: int, mom: dict, val: dict) -> str:
        if score >= 70:
            return "단기 상승 우위"
        if score >= 55:
            return "중립 — 보합 예상"
        if score >= 40:
            return "단기 하락 우위"
        return "강한 하락 우위"

    @staticmethod
    def _verdict(
        score: int, mom: dict, val: dict, vol: dict
    ) -> tuple[str, str]:
        reasons = []

        dev = mom.get("ma20_deviation")
        if dev is not None:
            reasons.append(f"MA20 이격도 {dev:.2%}")

        rsi = mom.get("rsi14")
        if rsi is not None:
            reasons.append(f"RSI {rsi:.1f}")

        per = val.get("per")
        if per is not None:
            reasons.append(f"PER {per:.1f}배")

        ann_vol = vol.get("annualized_vol")
        if ann_vol is not None:
            reasons.append(f"연환산변동성 {ann_vol:.1f}%")

        verdict = "진입 승인" if score >= 60 else "진입 보류"
        return verdict, f"퀀트점수 {score}점 — {', '.join(reasons)}"

    # ── RSI pandas 구현 ───────────────────────────────────────────────────────

    @staticmethod
    def _rsi_pandas(closes: pd.Series, period: int = 14) -> Optional[float]:
        """Wilder's RSI를 pandas rolling으로 계산한다."""
        if len(closes) < period + 1:
            return None
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        # Wilder's smoothing: EWM with alpha=1/period
        avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
        last_loss = float(avg_loss.iloc[-1])
        if last_loss == 0:
            return 100.0
        rs = float(avg_gain.iloc[-1]) / last_loss
        return 100.0 - (100.0 / (1.0 + rs))


# ── 더미 데이터 실행 예제 ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    import random

    random.seed(42)
    base = 55_000
    ohlcv_dummy = []
    price = base
    for _ in range(60):
        chg = random.uniform(-0.02, 0.02)
        close = round(price * (1 + chg))
        ohlcv_dummy.append({
            "close": close, "high": round(close * 1.01),
            "low": round(close * 0.99), "open": round(close * (1 - chg / 2)),
            "volume": random.randint(8_000_000, 25_000_000),
        })
        price = close

    dummy_data = {
        "current_price": ohlcv_dummy[-1]["close"],
        "per": 12.5,
        "pbr": 0.8,
        "ohlcv": ohlcv_dummy,
    }

    strategy = QuantStrategy()
    result = strategy.calculate_expected_return(dummy_data)
    print("=== QuantStrategy 결과 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
