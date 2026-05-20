"""
수익률 분석 라우터.

GET /api/v1/analysis/{stock_code}?strategy_type=dividend|quant

전략 유형에 따라 적절한 알고리즘을 동적으로 선택하여 실행하고,
Supabase upsert 직전의 최종 결과 JSON을 반환한다.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import verify_token
from app.services.kis_api import kis_client
from app.services.dart_client import collect_dart_data, extract_key_financials
from app.services.sector_per import get_sector_per
from app.services.analysis.base import StrategyValidationError
from app.services.analysis.dividend import DividendStrategy
from app.services.analysis.quant import QuantStrategy

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"], dependencies=[Depends(verify_token)])

KST = timezone(timedelta(hours=9))


# ── 전략 레지스트리 ───────────────────────────────────────────────────────────

_STRATEGY_MAP = {
    "dividend": DividendStrategy,
    "quant":    QuantStrategy,
}


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _float(val) -> Optional[float]:
    try:
        v = float(val) if val and float(val) != 0 else None
        return v
    except (ValueError, TypeError):
        return None


def _build_ohlcv(records: list[dict]) -> list[dict]:
    """KIS OHLCV output2(역순)를 오래된 순 정렬의 dict list로 변환한다."""
    result = []
    for r in reversed(records):  # output2는 최신→과거 순
        try:
            result.append({
                "close":  float(r.get("stck_clpr") or 0),
                "high":   float(r.get("stck_hgpr") or 0),
                "low":    float(r.get("stck_lwpr") or 0),
                "open":   float(r.get("stck_oprc") or 0),
                "volume": float(r.get("acml_vol") or 0),
            })
        except (ValueError, TypeError):
            continue
    return result


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.get("/{stock_code}")
async def run_analysis(
    stock_code: str,
    strategy_type: str = Query("quant", pattern="^(dividend|quant)$"),
):
    """
    strategy_type=dividend : GGM + 배당 안정성 분석 (DART 재무 데이터 필요)
    strategy_type=quant    : 모멘텀·가치·변동성 퀀트 점수 (KIS OHLCV 기반)

    반환 JSON에는 Supabase upsert 직전의 최종 구조가 포함됩니다.
    """
    import asyncio
    from datetime import date, timedelta

    today = date.today()
    start_date = (today - timedelta(days=130)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")

    # ── 1. KIS API: 현재가 + OHLCV 병렬 조회 ─────────────────────────────────
    try:
        price_data, ohlcv_data = await asyncio.gather(
            kis_client.get_stock_price(stock_code),
            kis_client.get_daily_ohlcv(stock_code, start_date, end_date),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KIS API 조회 실패: {e}")

    output = price_data.get("output", {})
    current_price = _float(output.get("stck_prpr"))
    if not current_price:
        raise HTTPException(status_code=404, detail=f"종목 {stock_code}의 현재가를 조회할 수 없습니다.")

    stock_name = output.get("hts_kor_isnm") or stock_code
    sector_name = output.get("bstp_kor_isnm") or None
    _, sector_per = get_sector_per(sector_name)

    per = _float(output.get("per"))
    pbr = _float(output.get("pbr"))
    roe = _float(output.get("roe"))
    eps = _float(output.get("eps"))
    bps = _float(output.get("bps"))

    ohlcv = _build_ohlcv(ohlcv_data.get("output2", []))

    # ── 2. 전략별 데이터 준비 ─────────────────────────────────────────────────
    strategy_data: dict = {
        "current_price": current_price,
        "per": per,
        "pbr": pbr,
        "roe": roe,
        "eps": eps,
        "bps": bps,
        "ohlcv": ohlcv,
    }

    dart_error: Optional[str] = None

    if strategy_type == "dividend":
        dart_result = await collect_dart_data(stock_code, n_years=3)
        dart_error = dart_result.get("error")

        fin_df = dart_result["financials"]
        div_df = dart_result["dividends"]

        # 배당 데이터를 dict list로 변환
        dividends: list[dict] = []
        if not div_df.empty:
            dividends = div_df.to_dict(orient="records")

        # 연도별 핵심 재무 계정 추출
        financials: list[dict] = []
        if not fin_df.empty:
            years_in_df = sorted(fin_df["year"].unique())
            for yr in years_in_df:
                kf = extract_key_financials(fin_df, yr)
                kf["year"] = yr
                financials.append(kf)

        strategy_data["dividends"] = dividends
        strategy_data["financials"] = financials

    # ── 3. 전략 실행 ──────────────────────────────────────────────────────────
    StrategyClass = _STRATEGY_MAP[strategy_type]
    strategy = StrategyClass()

    try:
        analysis_result = strategy.calculate_expected_return(strategy_data)
    except StrategyValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"[{strategy_type}] 분석 실패 ({stock_code}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"분석 실패: {e}")

    analyzed_at = datetime.now(KST).isoformat()

    # ── 4. Supabase upsert 직전 최종 결과 구조 ───────────────────────────────
    upsert_payload: dict = {
        # 공통 메타
        "stock_code": stock_code,
        "stock_name": stock_name,
        "strategy_type": strategy_type,
        "analyzed_at": analyzed_at,
        # 시세 스냅샷
        "current_price": current_price,
        "per": per,
        "pbr": pbr,
        "roe": roe,
        "sector_name": sector_name,
        "sector_per": sector_per,
        # 알고리즘 결과 (전략별 상이)
        **analysis_result,
    }

    return {
        "status": "success",
        "strategy_type": strategy_type,
        "data": upsert_payload,
        # DART 연동 오류가 있었으면 경고로 포함
        **({"dart_warning": dart_error} if dart_error else {}),
    }


# ── 더미 데이터 테스트 (python -m 실행 시) ───────────────────────────────────

if __name__ == "__main__":
    """
    실제 API 호출 없이 더미 데이터로 양쪽 전략을 검증한다.
    사용: cd backend && python -m app.routers.analysis
    """
    import json
    import random

    random.seed(0)

    # ── 공통 더미 OHLCV 생성 ─────────────────────────────────────────────────
    ohlcv_dummy: list[dict] = []
    price = 55_000.0
    for _ in range(90):
        chg = random.uniform(-0.025, 0.025)
        close = round(price * (1 + chg))
        ohlcv_dummy.append({
            "close": close, "high": round(close * 1.012),
            "low": round(close * 0.988), "open": round(close * (1 - chg / 2)),
            "volume": random.randint(5_000_000, 30_000_000),
        })
        price = close
    current_price = float(ohlcv_dummy[-1]["close"])

    # ── [1] QuantStrategy 테스트 ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(" QuantStrategy 더미 테스트")
    print("=" * 60)

    quant_data = {
        "current_price": current_price,
        "per": 12.5,
        "pbr": 0.82,
        "ohlcv": ohlcv_dummy,
    }
    quant_result = QuantStrategy().calculate_expected_return(quant_data)

    quant_payload: dict = {
        "stock_code": "005930",
        "stock_name": "삼성전자",
        "strategy_type": "quant",
        "analyzed_at": datetime.now(KST).isoformat(),
        "current_price": current_price,
        "per": 12.5,
        "pbr": 0.82,
        "roe": None,
        "sector_name": "전기·전자",
        "sector_per": 16.0,
        **quant_result,
    }
    print(json.dumps(quant_payload, ensure_ascii=False, indent=2))

    # ── [2] DividendStrategy 테스트 ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print(" DividendStrategy 더미 테스트")
    print("=" * 60)

    div_data = {
        "current_price": current_price,
        "roe": 12.5,
        "dividends": [
            {"year": 2022, "dps": 1_444, "payout_ratio": 25.0, "dividend_yield": 2.6},
            {"year": 2023, "dps": 1_444, "payout_ratio": 26.0, "dividend_yield": 2.8},
            {"year": 2024, "dps": 1_780, "payout_ratio": 27.0, "dividend_yield": 3.0},
        ],
        "financials": [
            {"year": 2022, "net_income": 546_000, "total_assets": 4_485_000,
             "total_liabilities": 992_000, "total_equity": 3_493_000,
             "operating_cf": 621_000, "capex": 53_000},
            {"year": 2023, "net_income": 155_000, "total_assets": 4_551_000,
             "total_liabilities": 1_001_000, "total_equity": 3_550_000,
             "operating_cf": 443_000, "capex": 67_000},
            {"year": 2024, "net_income": 320_000, "total_assets": 4_730_000,
             "total_liabilities": 1_050_000, "total_equity": 3_680_000,
             "operating_cf": 510_000, "capex": 70_000},
        ],
    }
    div_result = DividendStrategy().calculate_expected_return(div_data)

    div_payload: dict = {
        "stock_code": "005930",
        "stock_name": "삼성전자",
        "strategy_type": "dividend",
        "analyzed_at": datetime.now(KST).isoformat(),
        "current_price": current_price,
        "per": 12.5,
        "pbr": 0.82,
        "roe": 12.5,
        "sector_name": "전기·전자",
        "sector_per": 16.0,
        **div_result,
    }
    print(json.dumps(div_payload, ensure_ascii=False, indent=2))
