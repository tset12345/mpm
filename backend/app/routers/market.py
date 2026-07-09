"""
시장 현황 API - 트리맵, 지수 차트, 수급, ADR, 스파크라인, 주요 지표
"""
import asyncio
import logging
import time
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

import httpx
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


def _load_treemap_from_db(code_sector: dict[str, str]) -> list[dict]:
    """KIS inquire-price 전면 실패 시 stock_ohlcv DB 최근 2일로 fallback."""
    try:
        codes = list(code_sector.keys())
        start_iso = (date.today() - timedelta(days=10)).isoformat()
        rows = (
            supabase.table("stock_ohlcv")
            .select("stock_code,trade_date,close_price,volume")
            .in_("stock_code", codes)
            .gte("trade_date", start_iso)
            .order("trade_date", desc=True)
            .execute()
        ).data or []

        by_code: dict[str, list] = defaultdict(list)
        for r in rows:
            by_code[r["stock_code"]].append(r)

        result = []
        for code in codes:
            recs = by_code.get(code, [])
            if not recs:
                continue
            latest = recs[0]
            prev = recs[1] if len(recs) > 1 else None
            current_price = float(latest["close_price"])
            change_rate = 0.0
            if prev and float(prev["close_price"]) > 0:
                change_rate = round((current_price - float(prev["close_price"])) / float(prev["close_price"]) * 100, 2)
            result.append({
                "stock_code": code,
                "stock_name": code,
                "sector": code_sector[code],
                "current_price": current_price,
                "change_rate": change_rate,
                "market_cap": 0.0,
                "frgn_ntby_qty": 0.0,
                "org_ntby_qty": 0.0,
                "volume": float(latest["volume"]),
                "transaction_amount": 0.0,
                "source": "db_fallback",
            })
        return result
    except Exception as e:
        logger.warning(f"[market/treemap] DB fallback 실패: {e}")
        return []


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

    # KIS inquire-price 전면 장애 시 DB fallback
    if not data:
        logger.warning("[market/treemap] KIS 전면 실패 → stock_ohlcv DB fallback 사용")
        data = _load_treemap_from_db(code_sector)

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
def get_adr(days: int = Query(60, ge=1, le=365)):
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


# ── 시장 랭킹 ────────────────────────────────────────────────────────────────

_RANKINGS_DATA: dict = {}
_RANKINGS_AT: float = 0.0
_RANKINGS_TTL = 120  # 2분 캐시


def _parse_vol_item(r: dict) -> dict:
    return {
        "stock_code": r.get("mksc_shrn_iscd") or r.get("stck_shrn_iscd", ""),
        "stock_name": r.get("hts_kor_isnm", ""),
        "current_price": int(_sf(r.get("stck_prpr", 0))),
        "change_rate": _sf(r.get("prdy_ctrt", 0)),
        "volume": int(_sf(r.get("acml_vol", 0))),
        "amount": int(_sf(r.get("acml_tr_pbmn", 0))),
    }


def _parse_net_item(r: dict, net_field: str) -> dict:
    return {
        "stock_code": r.get("mksc_shrn_iscd") or r.get("stck_shrn_iscd", ""),
        "stock_name": r.get("hts_kor_isnm", ""),
        "current_price": int(_sf(r.get("stck_prpr", 0))),
        "change_rate": _sf(r.get("prdy_ctrt", 0)),
        "net_buy": int(_sf(r.get(net_field, 0))),
    }


def _parse_highlow_item(r: dict) -> dict:
    return {
        "stock_code": r.get("stck_shrn_iscd") or r.get("mksc_shrn_iscd", ""),
        "stock_name": r.get("hts_kor_isnm", ""),
        "current_price": int(_sf(r.get("stck_prpr", 0))),
        "change_rate": _sf(r.get("prdy_ctrt", 0)),
        "high_52w": int(_sf(r.get("w52_hgpr", 0))),
        "low_52w": int(_sf(r.get("w52_lwpr", 0))),
    }


@router.get("/rankings")
async def get_market_rankings(limit: int = Query(5, le=20)):
    """상승률/하락률/거래량/거래대금/외인/기관 순매수/52주신고가/신저가 상위 N (2분 캐시)"""
    global _RANKINGS_DATA, _RANKINGS_AT

    if time.time() - _RANKINGS_AT < _RANKINGS_TTL and _RANKINGS_DATA:
        data = _RANKINGS_DATA
        return {"status": "success", "data": {k: v[:limit] for k, v in data.items()}}

    try:
        vol_raw, amt_raw, frgn_raw, inst_raw, high52_raw, low52_raw = await asyncio.gather(
            kis_client.get_volume_ranking(),
            kis_client.get_trading_amount_ranking(),
            kis_client.get_foreign_net_buy_ranking(),       # fid_etc_cls_code=1
            kis_client.get_institution_net_buy_ranking(),   # fid_etc_cls_code=2
            kis_client.get_52week_high_low("1"),            # 신고가
            kis_client.get_52week_high_low("2"),            # 신저가
            return_exceptions=True,
        )

        def _out(raw) -> list:
            return raw.get("output", []) if isinstance(raw, dict) else []

        vol_items  = [_parse_vol_item(r)             for r in _out(vol_raw)]
        amt_items  = [_parse_vol_item(r)             for r in _out(amt_raw)]
        frgn_items = [_parse_net_item(r, "frgn_ntby_qty") for r in _out(frgn_raw)]
        inst_items = [_parse_net_item(r, "orgn_ntby_qty") for r in _out(inst_raw)]
        high52_items = [_parse_highlow_item(r) for r in _out(high52_raw) if r.get("stck_prpr")]
        low52_items  = [_parse_highlow_item(r) for r in _out(low52_raw)  if r.get("stck_prpr")]

        _RANKINGS_DATA = {
            "rise":             sorted(vol_items, key=lambda x: x["change_rate"], reverse=True),
            "fall":             sorted(vol_items, key=lambda x: x["change_rate"]),
            "volume":           vol_items,
            "amount":           sorted(amt_items, key=lambda x: x["amount"], reverse=True),
            "foreign_buy":      sorted(frgn_items, key=lambda x: x["net_buy"], reverse=True),
            "institution_buy":  sorted(inst_items, key=lambda x: x["net_buy"], reverse=True),
            "high_52w":         high52_items,
            "low_52w":          low52_items,
        }
        _RANKINGS_AT = time.time()
    except Exception as e:
        logger.warning(f"[market/rankings] 랭킹 조회 실패: {e}")
        if not _RANKINGS_DATA:
            return {"status": "error", "data": {}}

    data = _RANKINGS_DATA
    return {"status": "success", "data": {k: v[:limit] for k, v in data.items()}}


# ── 주요 시장 지표 (KOSPI·KOSDAQ·NASDAQ·USD/KRW) ──────────────────────────────

_INDICES_DATA: dict = {}
_INDICES_AT: float = 0.0
_INDICES_TTL = 60  # 1분 캐시

# Yahoo Finance 공유 클라이언트 — 매 호출 시 신규 생성 방지 (SSL context 누적 방지)
_YAHOO_CLIENT: httpx.AsyncClient | None = None


def _get_yahoo_client() -> httpx.AsyncClient:
    global _YAHOO_CLIENT
    if _YAHOO_CLIENT is None or _YAHOO_CLIENT.is_closed:
        _YAHOO_CLIENT = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible)"},
            timeout=10.0,
        )
    return _YAHOO_CLIENT


@router.get("/indices")
async def get_market_indices():
    """KOSPI, KOSDAQ, NASDAQ, USD/KRW 현재 지표 (1분 캐시)"""
    global _INDICES_DATA, _INDICES_AT

    if time.time() - _INDICES_AT < _INDICES_TTL and _INDICES_DATA:
        return {"status": "success", "data": _INDICES_DATA}

    today_str = date.today().strftime("%Y%m%d")
    week_ago = (date.today() - timedelta(days=7)).strftime("%Y%m%d")

    async def _fetch_korean_index(market_code: str, label: str) -> dict:
        try:
            raw = await kis_client.get_index_chart(market_code, week_ago, today_str, "D")
            out = raw.get("output1", {})
            return {
                "label": label,
                "price": _sf(out.get("bstp_nmix_prpr")),
                "change": _sf(out.get("bstp_nmix_prdy_vrss")),
                "change_rate": _sf(out.get("bstp_nmix_prdy_ctrt")),
                "sign": out.get("prdy_vrss_sign", "3"),
            }
        except Exception as e:
            logger.warning(f"[market/indices] {label} 조회 실패: {e}")
            return {"label": label, "price": None, "change": None, "change_rate": None, "sign": "3"}

    async def _fetch_yahoo(symbol: str, label: str) -> dict:
        try:
            import urllib.parse
            encoded = urllib.parse.quote(symbol)
            client = _get_yahoo_client()
            resp = await client.get(
                f"https://query2.finance.yahoo.com/v8/finance/chart/{encoded}?interval=1m&range=1d"
            )
            meta = resp.json()["chart"]["result"][0]["meta"]
            price = float(meta.get("regularMarketPrice") or 0)
            prev = float(meta.get("chartPreviousClose") or meta.get("previousClose") or 0)
            change = round(price - prev, 2)
            change_rate = round(change / prev * 100, 2) if prev else 0.0
            return {
                "label": label,
                "price": round(price, 2),
                "change": change,
                "change_rate": change_rate,
                "sign": "2" if change > 0 else "4" if change < 0 else "3",
            }
        except Exception as e:
            logger.warning(f"[market/indices] {label}({symbol}) 조회 실패: {e}")
            return {"label": label, "price": None, "change": None, "change_rate": None, "sign": "3"}

    kospi, kosdaq, nasdaq, dow, sp500, usd_krw, crude_oil, us10y = await asyncio.gather(
        _fetch_korean_index("0001", "KOSPI"),
        _fetch_korean_index("1001", "KOSDAQ"),
        _fetch_yahoo("^IXIC", "NASDAQ"),
        _fetch_yahoo("^DJI", "다우존스"),
        _fetch_yahoo("^GSPC", "S&P 500"),
        _fetch_yahoo("KRW=X", "USD/KRW"),
        _fetch_yahoo("CL=F", "WTI 유가"),
        _fetch_yahoo("^TNX", "미국 10년물"),
    )

    _INDICES_DATA = {
        "kospi": kospi, "kosdaq": kosdaq,
        "nasdaq": nasdaq, "dow": dow, "sp500": sp500,
        "usd_krw": usd_krw, "crude_oil": crude_oil, "us10y": us10y,
    }
    _INDICES_AT = time.time()
    return {"status": "success", "data": _INDICES_DATA}


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
