import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import verify_token
from app.models.schemas import StockSummary, StockDetail, StockMetrics, IchimokuData
from app.services.kis_api import kis_client
from app.services.supabase_client import supabase
from app.services import technical
from app.services.ichimoku import calculate as ichimoku_calculate
from app.services.sector_leader import (
    get_sector_leaders, SECTOR_STOCKS,
    get_sector_leaders_cached, get_all_sectors_cached, refresh_all_sectors,
)

logger = logging.getLogger(__name__)


def _recompute_scores(codes: list[str]) -> dict[str, dict]:
    """DB OHLCV로 기술 점수·태그를 실시간 재계산. {code: {score, tags, score_detail, strength}}"""
    if not codes:
        return {}
    start_iso = (date.today() - timedelta(days=130)).isoformat()
    try:
        rows = (
            supabase.table("stock_ohlcv")
            .select("stock_code,trade_date,high_price,low_price,close_price,volume")
            .in_("stock_code", codes)
            .gte("trade_date", start_iso)
            .order("trade_date")
            .execute()
        ).data or []
    except Exception:
        return {}

    by_code: dict[str, list[dict]] = {c: [] for c in codes}
    for r in rows:
        by_code[r["stock_code"]].append(r)

    result: dict[str, dict] = {}
    for code, ohlcv in by_code.items():
        if len(ohlcv) < 30:
            continue
        records = [
            {"stck_clpr": str(r["close_price"]), "stck_hgpr": str(r["high_price"]),
             "stck_lwpr": str(r["low_price"]), "acml_vol": str(r["volume"])}
            for r in ohlcv
        ]
        highs  = [float(r["stck_hgpr"]) for r in records]
        lows   = [float(r["stck_lwpr"]) for r in records]
        closes = [float(r["stck_clpr"]) for r in records]
        try:
            cloud = ichimoku_calculate(highs, lows, closes).get("position", "unknown")
        except Exception:
            cloud = "unknown"
        ta = technical.analyze(records, cloud_position=cloud)
        result[code] = ta
    return result

router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"], dependencies=[Depends(verify_token)])


class OHLCVSyncRequest(BaseModel):
    stock_codes: Optional[list[str]] = None


class FavoriteBody(BaseModel):
    stock_code: str
    stock_name: str


@router.get("/favorites")
def get_favorites():
    rows = supabase.table("favorites").select("stock_code,stock_name,created_at").order("created_at").execute()
    return {"status": "success", "data": rows.data or []}


@router.post("/favorites")
def add_favorite(body: FavoriteBody):
    supabase.table("favorites").upsert(
        {"stock_code": body.stock_code, "stock_name": body.stock_name}
    ).execute()
    return {"status": "success"}


@router.delete("/favorites/{stock_code}")
def remove_favorite(stock_code: str):
    supabase.table("favorites").delete().eq("stock_code", stock_code).execute()
    return {"status": "success"}


@router.get("/recommend")
async def get_recommendations():
    try:
        # 가장 최근 날짜 조회
        latest = supabase.table("stock_recommendations").select("date").order("date", desc=True).limit(1).execute()
        if not latest.data:
            return {"status": "success", "data": [], "date": None, "generated_at": None}
        latest_date = latest.data[0]["date"]
        # 해당 날짜의 종목을 total_score 내림차순으로 반환
        result = supabase.table("stock_recommendations").select("*").eq("date", latest_date).order("total_score", desc=True).execute()
        rows: list[dict] = result.data or []

        if not rows:
            return {"status": "success", "data": [], "date": latest_date, "generated_at": None}

        # 가장 최근 updated_at → generated_at
        generated_at = max(
            (r["updated_at"] for r in rows if r.get("updated_at")),
            default=None,
        )

        # 연속 추천 일수 + 최초 추천 가격 계산
        try:
            past = supabase.table("stock_recommendations") \
                .select("date,stock_code,entry_price") \
                .neq("date", latest_date) \
                .order("date", desc=True) \
                .limit(14 * 30) \
                .execute()
            past_data = past.data or []
            past_dates_sorted = sorted({r["date"] for r in past_data}, reverse=True)
            past_set = {(r["date"], r["stock_code"]) for r in past_data}
            past_entry_price: dict[tuple[str, str], int] = {
                (r["date"], r["stock_code"]): r["entry_price"]
                for r in past_data
                if r.get("entry_price")
            }
            for row in rows:
                streak = 1
                first_date = latest_date
                for d in past_dates_sorted:
                    if (d, row["stock_code"]) in past_set:
                        streak += 1
                        first_date = d
                    else:
                        break
                row["consecutive_days"] = streak
                # 최초 추천 시점 가격: streak>1이면 과거 첫 날짜의 entry_price
                if streak > 1:
                    row["first_entry_price"] = (
                        past_entry_price.get((first_date, row["stock_code"]))
                        or row.get("entry_price")
                    )
                else:
                    row["first_entry_price"] = row.get("entry_price")
        except Exception:
            for row in rows:
                row["consecutive_days"] = 1
                row["first_entry_price"] = row.get("entry_price")

        # 기술 점수·태그를 DB OHLCV 기준으로 실시간 재계산 (상세 페이지와 일치)
        try:
            codes = [r["stock_code"] for r in rows]
            fresh = _recompute_scores(codes)
            for row in rows:
                ta = fresh.get(row["stock_code"])
                if ta:
                    row["tech_score"]  = ta["score"]
                    row["total_score"] = ta["score"]
                    row["tags"]        = ta["tags"]
        except Exception as e:
            logger.warning(f"기술 점수 재계산 실패(저장값 사용): {e}")

        # stock_master에서 KOSPI/KOSDAQ 시장 구분 추가
        try:
            codes = [r["stock_code"] for r in rows]
            market_rows = supabase.table("stock_master").select("stock_code,market").in_("stock_code", codes).execute()
            market_map = {r["stock_code"]: r["market"] for r in (market_rows.data or [])}
            for row in rows:
                row["market"] = market_map.get(row["stock_code"])
        except Exception as e:
            logger.warning(f"시장 구분 조회 실패: {e}")

        rows.sort(key=lambda r: r.get("total_score") or 0, reverse=True)

        return {"status": "success", "data": rows, "date": latest_date, "generated_at": generated_at}
    except Exception as e:
        logger.warning(f"추천 종목 조회 실패: {e}")
        return {"status": "success", "data": [], "date": None, "generated_at": None}


@router.get("/recommend/prices")
async def get_recommendation_prices():
    """추천 종목 현재가·등락률만 실시간 KIS 조회 (프론트 폴링용)."""
    try:
        latest = supabase.table("stock_recommendations").select("date").order("date", desc=True).limit(1).execute()
        if not latest.data:
            return {"status": "success", "data": []}
        latest_date = latest.data[0]["date"]
        codes_res = supabase.table("stock_recommendations").select("stock_code").eq("date", latest_date).execute()
        codes = [r["stock_code"] for r in (codes_res.data or [])]
        if not codes:
            return {"status": "success", "data": []}

        async def _fetch(code: str) -> dict:
            try:
                out = (await kis_client.get_stock_price(code)).get("output", {})
                cp = out.get("stck_prpr")
                cr = out.get("prdy_ctrt")
                return {
                    "stock_code":   code,
                    "current_price": int(cp) if cp else None,
                    "change_rate":  float(cr) if cr is not None else None,
                }
            except Exception:
                return {"stock_code": code, "current_price": None, "change_rate": None}

        results = await asyncio.gather(*[_fetch(c) for c in codes], return_exceptions=True)
        data = [r for r in results if isinstance(r, dict)]
        return {"status": "success", "data": data}
    except Exception as e:
        logger.warning(f"추천 종목 가격 조회 실패: {e}")
        return {"status": "success", "data": []}


@router.get("/history")
def get_recommendation_history(type: str = Query("daily", pattern="^(daily|weekly|monthly)$")):
    """추천 종목 히스토리 조회. type: daily(7일) | weekly(4주) | monthly(6개월)"""
    try:
        from app.services.history import get_history
        data = get_history(type)
        return {"status": "success", "period_type": type, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/recommendations")
async def sync_recommendations():
    """추천 종목 수동 업데이트 (히스토리 저장 포함)"""
    try:
        from app.services.recommendations import update_recommendations
        from app.services.history import save_snapshot
        stocks = await update_recommendations()
        save_snapshot(stocks)
        return {"status": "success", "count": len(stocks), "data": stocks}
    except Exception as e:
        logger.error(f"추천 종목 동기화 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/ohlcv")
async def sync_ohlcv_endpoint(body: OHLCVSyncRequest = OHLCVSyncRequest()):
    """OHLCV 데이터 수동 동기화. body.stock_codes 미제공 시 거래량 상위 50종목 자동 조회."""
    try:
        from app.services.ohlcv_sync import sync_ohlcv
        result = await sync_ohlcv(body.stock_codes)
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"OHLCV 동기화 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_stocks(q: str = Query(..., min_length=1)):
    """종목명 검색 — stock_master 테이블(KOSPI·KOSDAQ 전체 종목) 기반."""
    try:
        result = supabase.table("stock_master") \
            .select("stock_code,stock_name,market") \
            .ilike("stock_name", f"%{q}%") \
            .order("stock_name") \
            .limit(50) \
            .execute()
        return {"status": "success", "data": result.data}
    except Exception as e:
        logger.warning(f"종목 검색 실패: {e}")
        return {"status": "success", "data": []}


@router.post("/sync/master")
async def sync_stock_master():
    """KRX에서 KOSPI·KOSDAQ 전체 종목 목록을 동기화."""
    try:
        from app.services.stock_master_sync import sync_stock_master as _sync
        result = await _sync()
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"종목 마스터 동기화 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{stock_code}/detail")
async def get_stock_detail(stock_code: str):
    from app.services.ichimoku import calculate as ichimoku_calculate
    from app.services import technical
    from app.services import expected_return as er_service
    from datetime import date, timedelta, datetime, timezone
    import asyncio

    def _float(val):
        try:
            return float(val) if val and float(val) != 0 else None
        except (ValueError, TypeError):
            return None

    today = date.today()
    start = (today - timedelta(days=130)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")

    try:
        price_data, ohlcv_data = await asyncio.gather(
            kis_client.get_stock_price(stock_code),
            kis_client.get_daily_ohlcv(stock_code, start, end),
        )
        fetched_at = datetime.now(timezone.utc).astimezone(
            timezone(timedelta(hours=9))
        ).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logger.warning(f"종목 {stock_code} 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"종목 데이터 조회 실패: {e}")

    # Look up stock name: recommendations table → history JSONB → fallback to code
    stock_name = stock_code
    try:
        row = supabase.table("stock_recommendations").select("stock_name").eq("stock_code", stock_code).limit(1).execute()
        if row.data:
            stock_name = row.data[0]["stock_name"]
        else:
            hist = supabase.table("recommendation_history").select("stocks").eq("period_type", "daily").order("period_key", desc=True).limit(10).execute()
            for h in (hist.data or []):
                match = next((s["stock_name"] for s in h.get("stocks", []) if s.get("stock_code") == stock_code), None)
                if match:
                    stock_name = match
                    break
    except Exception:
        pass

    output = price_data.get("output", {})
    kis_records = list(reversed(ohlcv_data.get("output2", [])))

    # DB 캐시(stock_ohlcv) 우선 사용 — 추천 목록과 동일한 데이터소스로 점수 일관성 확보
    records = kis_records
    try:
        start_iso = (today - timedelta(days=130)).isoformat()
        db_rows = (
            supabase.table("stock_ohlcv")
            .select("trade_date,open_price,high_price,low_price,close_price,volume")
            .eq("stock_code", stock_code)
            .gte("trade_date", start_iso)
            .order("trade_date")
            .execute()
        ).data or []
        if len(db_rows) >= 30:
            records = [
                {
                    "stck_clpr": str(r["close_price"]),
                    "stck_hgpr": str(r["high_price"]),
                    "stck_lwpr": str(r["low_price"]),
                    "acml_vol":  str(r["volume"]),
                }
                for r in db_rows
            ]
    except Exception:
        pass  # KIS API 결과로 폴백

    highs, lows, closes = [], [], []
    for r in records:
        try:
            highs.append(float(r.get("stck_hgpr") or 0))
            lows.append(float(r.get("stck_lwpr") or 0))
            closes.append(float(r.get("stck_clpr") or 0))
        except (ValueError, TypeError):
            continue

    ichimoku = ichimoku_calculate(highs, lows, closes)
    ta = technical.analyze(records, cloud_position=ichimoku.get("position", "unknown"))

    # 기대 수익률 분석 — Bollinger 하단을 기술적 손절가로 우선 사용
    from app.services.sector_per import get_sector_per
    _cur = _float(output.get("stck_prpr"))
    _eps = _float(output.get("eps"))
    _bps = _float(output.get("bps"))
    _roe = _float(output.get("roe"))
    _bb_lower = ta["signals"].get("bb_lower")
    _stop = _bb_lower if (_bb_lower and _cur and _bb_lower < _cur) else None
    _raw_sector = output.get("bstp_kor_isnm") or None
    _matched_sector, _sector_per = get_sector_per(_raw_sector)
    er = er_service.compute(
        current_price=_cur or 0,
        eps=_eps,
        bps=_bps,
        roe=_roe,
        stop_loss=_stop,
        target_per=_sector_per,
    ) if _cur else None
    if er is not None:
        er["sector_name"] = _raw_sector
        er["sector_per"] = _sector_per

    def _int(val):
        try:
            v = int(val) if val else None
            return v if v else None
        except (ValueError, TypeError):
            return None

    # stock_master에서 KOSPI/KOSDAQ 시장 구분 조회
    market: str | None = None
    try:
        mrow = supabase.table("stock_master").select("market").eq("stock_code", stock_code).limit(1).execute()
        if mrow.data:
            market = mrow.data[0]["market"]
    except Exception:
        pass

    return {
        "status": "success",
        "data": {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "market": market,
            "fetched_at": fetched_at,
            "current_price": _float(output.get("stck_prpr")),
            "change_rate": _float(output.get("prdy_ctrt")),
            "change_amount": _float(output.get("prdy_vrss")),
            "volume": _float(output.get("acml_vol")),
            "price_info": {
                "ref_price":    _int(output.get("stck_sdpr")),   # 기준가 (전일 종가)
                "open":         _int(output.get("stck_oprc")),   # 시가
                "high":         _int(output.get("stck_hgpr")),   # 고가
                "low":          _int(output.get("stck_lwpr")),   # 저가
                "upper_limit":  _int(output.get("stck_mxpr")),   # 상한가
                "lower_limit":  _int(output.get("stck_llam")),   # 하한가
                "w52_high":     _int(output.get("w52_hgpr")),    # 52주 최고가
                "w52_low":      _int(output.get("w52_lwpr")),    # 52주 최저가
                "market_cap":   _int(output.get("hts_avls")),    # 시가총액 (억원)
                "trade_amount": _float(output.get("acml_tr_pbmn")),  # 거래대금 (원)
                "foreign_rate": _float(output.get("hts_frgn_ehrt")), # 외국인 보유율 (%)
                "eps":          _float(output.get("eps")),        # EPS
                "bps":          _float(output.get("bps")),        # BPS
            },
            "metrics": {
                "per": _float(output.get("per")),
                "pbr": _float(output.get("pbr")),
                "roe": _float(output.get("roe")),
            },
            "ichimoku": ichimoku,
            "expected_return": er,
            "technical": {
                "score": ta["score"],
                "tags": ta["tags"],
                "signals": ta["signals"],
                "score_detail": ta["score_detail"],
                "strength": ta["strength"],
            },
        },
    }


@router.get("/sector-leader/all")
async def get_all_sector_leaders():
    """모든 섹터의 캐시된 주도주 데이터를 한 번에 반환."""
    data = await get_all_sectors_cached()
    return {"status": "success", "data": data}


@router.post("/sector-leader/refresh")
async def refresh_sector_leaders():
    """모든 섹터를 KIS API에서 재조회해 DB에 저장 (스케줄러 또는 수동 갱신)."""
    await refresh_all_sectors()
    return {"status": "success", "message": f"{len(SECTOR_STOCKS)}개 섹터 갱신 완료"}


@router.get("/sector-leader")
async def get_sector_leader(sector: str = Query(...), force: bool = Query(False)):
    if sector not in SECTOR_STOCKS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 섹터입니다: {sector}")
    leaders, updated_at = await get_sector_leaders_cached(sector, force=force)
    return {"status": "success", "sector": sector, "data": leaders, "updated_at": updated_at}


@router.get("/health")
async def health():
    return {"status": "ok"}
