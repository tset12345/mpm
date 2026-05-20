import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import verify_token
from app.services.supabase_client import supabase
from app.services.portfolio_analysis import (
    compute_holdings_hash,
    run_analysis,
    is_stale,
)
from app.routers.holdings import _fetch_current_prices, _enrich

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"], dependencies=[Depends(verify_token)])


class AnalysisRequest(BaseModel):
    profile_id: Optional[int] = None


def _get_cached(profile_id: Optional[int]) -> Optional[dict]:
    try:
        q = supabase.table("portfolio_analyses").select("*")
        if profile_id is None:
            q = q.is_("profile_id", "null")
        else:
            q = q.eq("profile_id", profile_id)
        result = q.limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.warning(f"포트폴리오 분석 캐시 조회 실패: {e}")
        return None


def _upsert(profile_id: Optional[int], text: str, holdings_hash: str):
    record = {
        "analysis_text": text,
        "holdings_hash": holdings_hash,
        "updated_at": "now()",
    }
    cached = _get_cached(profile_id)
    if cached:
        supabase.table("portfolio_analyses").update(record).eq("id", cached["id"]).execute()
    else:
        if profile_id is not None:
            record["profile_id"] = profile_id
        supabase.table("portfolio_analyses").insert(record).execute()


async def _load_enriched_holdings(profile_id: Optional[int]) -> list[dict]:
    q = supabase.table("holdings").select("*").order("created_at")
    if profile_id is not None:
        q = q.eq("profile_id", profile_id)
    result = q.execute()
    rows: list[dict] = result.data or []
    if not rows:
        return []
    codes = list({r["stock_code"] for r in rows})
    prices, price_times = await _fetch_current_prices(codes)
    return [_enrich(r, prices, price_times) for r in rows]


@router.get("/analysis")
async def get_analysis(
    profile_id: Optional[int] = Query(None),
    holdings_hash: Optional[str] = Query(None),
):
    """캐시된 분석 결과를 반환. holdings_hash를 전달하면 최신 여부(is_stale)도 함께 반환."""
    cached = _get_cached(profile_id)
    if not cached:
        return {"status": "success", "data": None, "is_stale": True}

    stale = is_stale(cached, holdings_hash or "") if holdings_hash else False
    return {
        "status": "success",
        "data": {
            "analysis_text": cached["analysis_text"],
            "updated_at": cached["updated_at"],
        },
        "is_stale": stale,
    }


@router.post("/analysis")
async def create_analysis(body: AnalysisRequest):
    """보유 종목을 조회해 Gemini 분석 실행 후 결과를 저장하고 반환."""
    holdings = await _load_enriched_holdings(body.profile_id)
    if not holdings:
        raise HTTPException(status_code=400, detail="분석할 보유 종목이 없습니다.")

    h_hash = compute_holdings_hash(holdings)

    # 오늘 날짜 + 동일 해시면 캐시 재사용
    cached = _get_cached(body.profile_id)
    if cached and not is_stale(cached, h_hash):
        return {
            "status": "success",
            "data": {
                "analysis_text": cached["analysis_text"],
                "updated_at": cached["updated_at"],
            },
            "is_stale": False,
        }

    # 프로필명 및 분석 유형 결정
    profile_name = "투자자"
    analysis_type = "quant"
    if body.profile_id is not None:
        try:
            p = supabase.table("profiles").select("name,analysis_type").eq("id", body.profile_id).limit(1).execute()
            if p.data:
                profile_name = p.data[0]["name"]
                analysis_type = p.data[0].get("analysis_type") or "quant"
        except Exception:
            pass

    try:
        text = await run_analysis(holdings, profile_name, analysis_type)
    except Exception as e:
        logger.error(f"포트폴리오 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"AI 분석 실패: {e}")

    try:
        _upsert(body.profile_id, text, h_hash)
    except Exception as e:
        logger.warning(f"분석 결과 저장 실패: {e}")

    return {
        "status": "success",
        "data": {"analysis_text": text, "updated_at": None},
        "is_stale": False,
    }
