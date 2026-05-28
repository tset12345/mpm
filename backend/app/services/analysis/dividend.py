"""
배당형 기대 수익률 분석 (DividendStrategy).

알고리즘:
  1. 고든 성장 모델(GGM):
       기대수익률(%) = (D1 / P0 × 100) + g
       D1 = D0 × (1 + g)   ← 내년 예상 배당금
       g  = min(ROE × 사내유보율, 과거 DPS 성장률 평균)
  2. 배당 안정성 점수(0-100):
       FCF 양수 여부      +25
       부채비율           +25 / +15 / +5 / 0
       배당성향           +25 / +15 / +10 / +5 / 감점
       DPS 성장 연속성    +15
       순이익 흑자 지속   +10
  3. 등급: ≥70=안정  40~69=모니터링  <40=위험

입력(data dict) 예시:
  {
    "current_price": 55000,
    "roe": 12.5,          # % (KIS API output 기준)
    "dividends": [        # DART, 오래된 연도 → 최근 연도 순
      {"year": 2022, "dps": 1444, "payout_ratio": 25.0, "dividend_yield": 2.6},
      {"year": 2023, "dps": 1444, "payout_ratio": 26.0, "dividend_yield": 2.8},
      {"year": 2024, "dps": 1444, "payout_ratio": 27.0, "dividend_yield": 2.9},
    ],
    "financials": [       # DART 연도별 핵심 계정
      {"year": 2022, "net_income": 546000000, "total_assets": 4485000000,
       "total_liabilities": 992000000, "total_equity": 3493000000,
       "operating_cf": 621000000, "capex": 53000000},
      ...
    ],
  }
"""

from __future__ import annotations

from typing import Optional

from .base import BaseStrategy, StrategyValidationError


class DividendStrategy(BaseStrategy):
    REQUIRED_KEYS = ["current_price", "dividends"]

    # ── 공개 인터페이스 ────────────────────────────────────────────────────────

    def calculate_expected_return(self, data: dict) -> dict:
        """배당형 기대 수익률 + 안정성 점수를 계산한다."""
        self.validate(data)

        current_price: float = data["current_price"]
        roe: Optional[float] = data.get("roe")
        dividends: list[dict] = data["dividends"]
        financials: list[dict] = data.get("financials", [])

        import pandas as pd
        div_df = pd.DataFrame(dividends).sort_values("year").reset_index(drop=True)
        fin_df = pd.DataFrame(financials).sort_values("year").reset_index(drop=True) if financials else pd.DataFrame()

        # ── GGM 계산 ──────────────────────────────────────────────────────────
        d0, g, d1, div_yield, ggm_return, payout_latest = self._ggm(div_df, current_price, roe)

        # ── 안정성 점수 ───────────────────────────────────────────────────────
        score_detail, stability_score = self._stability_score(div_df, fin_df, payout_latest)
        stability_grade = self._grade(stability_score)

        # ── 진입 판단 ─────────────────────────────────────────────────────────
        verdict, verdict_reason = self._verdict(ggm_return, stability_score, div_yield)

        return {
            # GGM
            "d0": round(d0, 2) if d0 is not None else None,
            "d1": round(d1, 2) if d1 is not None else None,
            "dividend_growth_rate": round(g * 100, 2) if g is not None else None,   # %
            "dividend_yield": round(div_yield, 2) if div_yield is not None else None, # %
            "ggm_expected_return": round(ggm_return, 2) if ggm_return is not None else None, # %
            # 안정성
            "stability_score": stability_score,
            "stability_grade": stability_grade,
            "stability_detail": score_detail,
            # 진입 판단
            "verdict": verdict,
            "verdict_reason": verdict_reason,
        }

    # ── 내부 계산 ─────────────────────────────────────────────────────────────

    def _ggm(
        self,
        div_df: pd.DataFrame,
        current_price: float,
        roe: Optional[float],
    ) -> tuple:
        """(d0, g, d1, div_yield, ggm_return, payout_latest) 반환."""
        dps_col = div_df["dps"].dropna()
        if dps_col.empty:
            return None, None, None, None, None, None

        d0: float = float(dps_col.iloc[-1])
        payout_latest: Optional[float] = None
        if "payout_ratio" in div_df.columns:
            pr = div_df["payout_ratio"].dropna()
            if not pr.empty:
                payout_latest = float(pr.iloc[-1])

        # g 계산: 두 가지 방법 중 작은 값 사용
        g_hist: Optional[float] = self._historical_growth(dps_col)
        g_sustainable: Optional[float] = None
        if roe is not None and payout_latest is not None:
            retention = max(0.0, 1.0 - payout_latest / 100.0)
            g_sustainable = (roe / 100.0) * retention

        candidates = [v for v in [g_hist, g_sustainable] if v is not None]
        if not candidates:
            g = 0.0
        else:
            g = min(candidates)    # 보수적: 두 방법 중 낮은 값
        g = max(-0.05, min(g, 0.15))   # -5% ~ 15% 클리핑

        d1 = d0 * (1.0 + g)
        div_yield = d0 / current_price * 100.0
        ggm_return = (d1 / current_price * 100.0) + g * 100.0

        return d0, g, d1, div_yield, ggm_return, payout_latest

    @staticmethod
    def _historical_growth(dps_series: pd.Series) -> Optional[float]:
        """DPS 시계열의 연평균 성장률(CAGR)을 반환한다."""
        values = dps_series.dropna().tolist()
        if len(values) < 2:
            return None
        first, last = values[0], values[-1]
        if first <= 0 or last <= 0:
            return None
        n = len(values) - 1
        return (last / first) ** (1.0 / n) - 1.0

    def _stability_score(
        self, div_df: pd.DataFrame, fin_df: pd.DataFrame, payout_latest: Optional[float]
    ) -> tuple[list[dict], int]:
        """배당 안정성 점수(0~100)와 항목별 상세를 반환한다."""
        import pandas as pd
        detail: list[dict] = []
        total = 0

        def add(name: str, pts: int, reason: str) -> None:
            nonlocal total
            detail.append({"name": name, "score": pts, "reason": reason})
            total += pts

        # 1. 잉여현금흐름(FCF = 영업CF - CAPEX) 양수 여부 (+25)
        if not fin_df.empty and "operating_cf" in fin_df.columns:
            latest_fin = fin_df.dropna(subset=["operating_cf"]).tail(1)
            if not latest_fin.empty:
                ocf = float(latest_fin["operating_cf"].iloc[0] or 0)
                capex = float((latest_fin.get("capex", pd.Series([0])).iloc[0]) or 0)
                fcf = ocf - abs(capex)
                if fcf > 0:
                    add("FCF 양수", 25, f"잉여현금흐름 양수 ({fcf:+,.0f}) — 배당 재원 충분")
                else:
                    add("FCF 양수", 0, f"잉여현금흐름 음수 ({fcf:+,.0f}) — 배당 재원 부족")
        else:
            add("FCF 양수", 10, "FCF 데이터 없음 (중립 부여)")

        # 2. 부채비율 (총부채 / 자본총계 × 100) (+25 max)
        if not fin_df.empty and "total_liabilities" in fin_df.columns:
            latest = fin_df.dropna(subset=["total_liabilities", "total_equity"]).tail(1)
            if not latest.empty:
                liab = float(latest["total_liabilities"].iloc[0] or 0)
                eq = float(latest["total_equity"].iloc[0] or 1)
                debt_ratio = liab / eq * 100.0
                if debt_ratio <= 100:
                    add("부채비율", 25, f"부채비율 {debt_ratio:.1f}% — 재무구조 안정")
                elif debt_ratio <= 150:
                    add("부채비율", 15, f"부채비율 {debt_ratio:.1f}% — 양호")
                elif debt_ratio <= 200:
                    add("부채비율", 5, f"부채비율 {debt_ratio:.1f}% — 모니터링 필요")
                else:
                    add("부채비율", 0, f"부채비율 {debt_ratio:.1f}% — 고레버리지 위험")
        else:
            add("부채비율", 10, "부채비율 데이터 없음 (중립 부여)")

        # 3. 배당성향(payout ratio) (+25 max, 과도 시 감점)
        if payout_latest is not None:
            if 30 <= payout_latest <= 60:
                add("배당성향", 25, f"배당성향 {payout_latest:.1f}% — 이상적 구간(30~60%)")
            elif 20 <= payout_latest < 30 or 60 < payout_latest <= 70:
                add("배당성향", 15, f"배당성향 {payout_latest:.1f}% — 양호")
            elif 70 < payout_latest <= 80:
                add("배당성향", 10, f"배당성향 {payout_latest:.1f}% — 다소 높음")
            elif payout_latest < 20:
                add("배당성향", 5, f"배당성향 {payout_latest:.1f}% — 낮음(성장 중심)")
            else:  # > 80
                pts = max(0, 25 - int((payout_latest - 80) * 2.5))
                add("배당성향", pts, f"배당성향 {payout_latest:.1f}% — 지속 가능성 우려(80% 초과)")
        else:
            add("배당성향", 10, "배당성향 데이터 없음 (중립 부여)")

        # 4. DPS 성장 연속성 (+15)
        dps_vals = div_df["dps"].dropna().tolist()
        if len(dps_vals) >= 2:
            consistently_growing = all(b >= a for a, b in zip(dps_vals, dps_vals[1:]))
            if consistently_growing:
                add("배당 성장 연속성", 15, f"{len(dps_vals)}년 연속 DPS 유지·증가")
            else:
                add("배당 성장 연속성", 0, "DPS 감소 이력 존재")
        else:
            add("배당 성장 연속성", 5, "데이터 부족 (부분 점수)")

        # 5. 순이익 흑자 지속 (+10)
        if not fin_df.empty and "net_income" in fin_df.columns:
            ni_vals = fin_df["net_income"].dropna().tolist()
            if ni_vals and all(v > 0 for v in ni_vals):
                add("순이익 흑자", 10, f"최근 {len(ni_vals)}년 연속 흑자")
            elif ni_vals:
                add("순이익 흑자", 0, "적자 발생 이력 있음")
        else:
            add("순이익 흑자", 5, "데이터 없음 (부분 점수)")

        return detail, min(100, max(0, total))

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 70:
            return "안정"
        if score >= 40:
            return "모니터링"
        return "위험"

    @staticmethod
    def _verdict(
        ggm_return: Optional[float],
        stability_score: int,
        div_yield: Optional[float],
    ) -> tuple[str, str]:
        if ggm_return is None:
            return "판단 불가", "배당 데이터 부족으로 GGM 계산 불가"

        reasons = []
        approved = True

        # 최소 기대 수익률 8% (요구수익률 COE 기준)
        if ggm_return < 8.0:
            approved = False
            reasons.append(f"GGM 기대수익률 {ggm_return:.1f}% — 요구수익률(8%) 미달")
        else:
            reasons.append(f"GGM 기대수익률 {ggm_return:.1f}%")

        # 안정성
        if stability_score < 40:
            approved = False
            reasons.append(f"배당 안정성 점수 {stability_score}점(위험)")
        else:
            reasons.append(f"안정성 {stability_score}점({DividendStrategy._grade(stability_score)})")

        verdict = "진입 승인" if approved else "진입 보류"
        return verdict, " / ".join(reasons)


# ── 더미 데이터 실행 예제 ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    dummy_data = {
        "current_price": 55_000,
        "roe": 12.5,
        "dividends": [
            {"year": 2022, "dps": 1_444, "payout_ratio": 25.0, "dividend_yield": 2.6},
            {"year": 2023, "dps": 1_444, "payout_ratio": 26.0, "dividend_yield": 2.8},
            {"year": 2024, "dps": 1_780, "payout_ratio": 27.0, "dividend_yield": 3.0},
        ],
        "financials": [
            {"year": 2022, "net_income": 546_000_000, "total_assets": 4_485_000_000,
             "total_liabilities": 992_000_000, "total_equity": 3_493_000_000,
             "operating_cf": 621_000_000, "capex": 53_000_000},
            {"year": 2023, "net_income": 155_000_000, "total_assets": 4_551_000_000,
             "total_liabilities": 1_001_000_000, "total_equity": 3_550_000_000,
             "operating_cf": 443_000_000, "capex": 67_000_000},
            {"year": 2024, "net_income": 320_000_000, "total_assets": 4_730_000_000,
             "total_liabilities": 1_050_000_000, "total_equity": 3_680_000_000,
             "operating_cf": 510_000_000, "capex": 70_000_000},
        ],
    }

    strategy = DividendStrategy()
    result = strategy.calculate_expected_return(dummy_data)
    print("=== DividendStrategy 결과 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
