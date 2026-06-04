"""
시장 현황 API - 트리맵, 지수 차트, 수급, ADR, 스파크라인
"""
import asyncio
import logging
import time
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.auth import verify_token
from app.services.kis_api import kis_client
from app.services.sector_leader import SECTOR_STOCKS
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/market", tags=["market"], dependencies=[Depends(verify_token)])

# ── 트리맵 캐시 ──────────────────────────────────────────────────────────────
_TREEMAP_DATA: list[dict] = []
_TREEMAP_AT: float = 0.0
_TREEMAP_TTL = 180  # 3분

_KIS_SEM = asyncio.Semaphore(5)


def _fmt_date(d: str) -> str:
    """YYYYMMDD → YYYY-MM-DD (lightweight-charts 요구 형식)"""
    d = (d or "").strip()
    if len(d) == 8 and d.isdigit():
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return d


def _sf(val, default: float = 0.0) -> float:
    try:
        return float(str(val).replace("+", "").replace(",", "").strip()) if val else default
    except Exception:
        return default


async def _fetch_stock(code: str, sector: str) -> dict | None:
    async with _KIS_SEM:
        try:
            data = await kis_client.get_stock_price(code)
            out = data.get("output", {})
            return {
                "stock_code": code,
                "stock_name": out.get("hts_kor_isnm") or code,
                "sector": sector,
                "current_price": _sf(out.get("stck_prpr")),
                "change_rate": _sf(out.get("prdy_ctrt")),
                "market_cap": _sf(out.get("hts_avls")),   # 억원
                "frgn_ntby_qty": _sf(out.get("frgn_ntby_qty")),
                "org_ntby_qty": 0.0,
                "volume": _sf(out.get("acml_vol")),
                "transaction_amount": _sf(out.get("acml_tr_pbmn")),
            }
        except Exception as e:
            logger.warning(f"[market/treemap] KIS 조회 실패 {code}: {e}")
            return None


@router.get("/treemap")
async def get_treemap(sort: str = Query("change_rate")):
    """SECTOR_STOCKS 유니버스 전체 종목 데이터 (3분 캐시)"""
    global _TREEMAP_DATA, _TREEMAP_AT

    if time.time() - _TREEMAP_AT < _TREEMAP_TTL and _TREEMAP_DATA:
        return _sorted_treemap(_TREEMAP_DATA, sort)

    # 중복 없이 code→sector 매핑
    code_sector: dict[str, str] = {}
    for sector, codes in SECTOR_STOCKS.items():
        for code in codes:
            if code not in code_sector:
                code_sector[code] = sector

    results = await asyncio.gather(
        *[_fetch_stock(c, s) for c, s in code_sector.items()],
        return_exceptions=True,
    )
    data = [r for r in results if isinstance(r, dict)]

    # 기관/외국인 순매수 보강 (ranking API)
    try:
        rank = await kis_client.get_institution_foreign_net_buy_ranking()
        rank_items = rank.get("output", [])
        nb_map: dict[str, dict] = {}
        for item in rank_items:
            c = item.get("mksc_shrn_iscd") or item.get("stck_shrn_iscd") or ""
            if c:
                nb_map[c] = {
                    "frgn_ntby_qty": _sf(item.get("frgn_ntby_qty")),
                    "org_ntby_qty": _sf(item.get("orgn_ntby_qty")),
                }
        for item in data:
            if item["stock_code"] in nb_map:
                item["frgn_ntby_qty"] = nb_map[item["stock_code"]]["frgn_ntby_qty"]
                item["org_ntby_qty"] = nb_map[item["stock_code"]]["org_ntby_qty"]
    except Exception as e:
        logger.warning(f"[market/treemap] 수급 보강 실패: {e}")

    # stock_master에서 한글 종목명 보강
    try:
        codes = [item["stock_code"] for item in data]
        master_rows = supabase.table("stock_master").select("stock_code,stock_name").in_("stock_code", codes).execute()
        name_map = {r["stock_code"]: r["stock_name"] for r in (master_rows.data or [])}
        for item in data:
            if item["stock_code"] in name_map:
                item["stock_name"] = name_map[item["stock_code"]]
    except Exception as e:
        logger.warning(f"[market/treemap] stock_master 종목명 보강 실패: {e}")

    _TREEMAP_DATA = data
    _TREEMAP_AT = time.time()
    return _sorted_treemap(data, sort)


def _sorted_treemap(data: list[dict], sort: str) -> dict:
    key_map = {
        "frgn_net_buy": lambda x: x.get("frgn_ntby_qty", 0),
        "org_net_buy": lambda x: x.get("org_ntby_qty", 0),
    }
    key_fn = key_map.get(sort, lambda x: x.get("change_rate", 0))
    return {"status": "success", "data": sorted(data, key=key_fn, reverse=True)}


# ── 지수 차트 ─────────────────────────────────────────────────────────────────

@router.get("/index-chart")
async def get_index_chart(
    market: str = Query("KOSPI"),
    period: str = Query("D"),  # D, W, M
):
    """KOSPI/KOSDAQ 지수 기간별 시세"""
    market_code = "0001" if market == "KOSPI" else "1001"
    today = date.today()
    days_map = {"D": 180, "W": 365, "M": 365 * 3}
    start = (today - timedelta(days=days_map.get(period, 180))).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")

    try:
        raw = await kis_client.get_index_chart(market_code, start, end, period)
        # output2 → 리스트 (날짜 역순이므로 reverse)
        items = list(reversed(raw.get("output2", [])))
        candles = [
            {
                "date": _fmt_date(it.get("stck_bsop_date") or it.get("bass_dt") or ""),
                "open": _sf(it.get("bstp_nmix_oprc")),
                "high": _sf(it.get("bstp_nmix_hgpr")),
                "low": _sf(it.get("bstp_nmix_lwpr")),
                "close": _sf(it.get("bstp_nmix_prpr")),
                "volume": _sf(it.get("acml_vol")),
                "frgn_ntby": _sf(it.get("frgn_ntby_qty")),
            }
            for it in items
            if it.get("bstp_nmix_prpr")
        ]
        return {"status": "success", "market": market, "period": period, "data": candles}
    except Exception as e:
        logger.warning(f"[market/index-chart] 조회 실패: {e}")
        return {"status": "error", "market": market, "period": period, "data": [], "detail": str(e)}


# ── 수급 집계 ─────────────────────────────────────────────────────────────────

@router.get("/investor-trend")
async def get_investor_trend():
    """기관·외국인 순매수 상위 종목 집계 (ranking API 기반)"""
    try:
        rank = await kis_client.get_institution_foreign_net_buy_ranking()
        items = rank.get("output", [])[:50]
        total_frgn = sum(_sf(r.get("frgn_ntby_qty")) for r in items)
        total_org = sum(_sf(r.get("orgn_ntby_qty")) for r in items)
        stocks = [
            {
                "stock_code": r.get("mksc_shrn_iscd") or r.get("stck_shrn_iscd"),
                "stock_name": r.get("hts_kor_isnm"),
                "change_rate": _sf(r.get("prdy_ctrt")),
                "frgn_ntby_qty": _sf(r.get("frgn_ntby_qty")),
                "org_ntby_qty": _sf(r.get("orgn_ntby_qty")),
            }
            for r in items
        ]
        return {
            "status": "success",
            "data": {
                "foreign_net_buy": total_frgn,
                "institution_net_buy": total_org,
                "individual_net_buy": -(total_frgn + total_org),
                "stocks": stocks,
            },
        }
    except Exception as e:
        logger.warning(f"[market/investor-trend] 조회 실패: {e}")
        return {"status": "error", "data": None}


# ── ADR ───────────────────────────────────────────────────────────────────────

@router.get("/adr")
def get_adr(days: int = Query(60)):
    """등락비율(ADR) — stock_ohlcv DB에서 계산"""
    try:
        start_iso = (date.today() - timedelta(days=days + 10)).isoformat()
        rows = (
            supabase.table("stock_ohlcv")
            .select("stock_code,trade_date,close_price")
            .gte("trade_date", start_iso)
            .order("trade_date")
            .execute()
        ).data or []

        # stock_code → [(date, close), ...]
        by_stock: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for r in rows:
            by_stock[r["stock_code"]].append((r["trade_date"], float(r["close_price"])))

        all_dates = sorted({r["trade_date"] for r in rows})
        adr_series: list[dict] = []

        for i, d in enumerate(all_dates[1:], 1):
            prev_d = all_dates[i - 1]
            advancing = declining = 0
            for closes in by_stock.values():
                closes_map = {c[0]: c[1] for c in closes}
                cur = closes_map.get(d)
                prv = closes_map.get(prev_d)
                if cur is not None and prv is not None:
                    if cur > prv:
                        advancing += 1
                    elif cur < prv:
                        declining += 1
            total = advancing + declining
            if total > 0:
                adr_series.append({
                    "date": d,
                    "advancing": advancing,
                    "declining": declining,
                    "adr": round(advancing / total * 100, 1),
                })

        return {"status": "success", "data": adr_series[-days:]}
    except Exception as e:
        logger.warning(f"[market/adr] 계산 실패: {e}")
        return {"status": "success", "data": []}


# ── 스파크라인 ────────────────────────────────────────────────────────────────

@router.get("/sparkline/{code}")
def get_sparkline(code: str, days: int = Query(5)):
    """종목 스파크라인 — stock_ohlcv DB에서 최근 N일 종가 반환"""
    try:
        start_iso = (date.today() - timedelta(days=days + 5)).isoformat()
        rows = (
            supabase.table("stock_ohlcv")
            .select("trade_date,close_price")
            .eq("stock_code", code)
            .gte("trade_date", start_iso)
            .order("trade_date", desc=True)
            .limit(days)
            .execute()
        ).data or []
        rows = list(reversed(rows))
        return {
            "status": "success",
            "data": [{"date": r["trade_date"], "close": float(r["close_price"])} for r in rows],
        }
    except Exception as e:
        logger.warning(f"[market/sparkline] 조회 실패 {code}: {e}")
        return {"status": "success", "data": []}
