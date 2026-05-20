import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import verify_token
from app.services.supabase_client import supabase
from app.services.kis_api import kis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/holdings", tags=["holdings"], dependencies=[Depends(verify_token)])


class HoldingCreate(BaseModel):
    stock_code: str
    stock_name: str
    avg_price: int
    quantity: int
    memo: Optional[str] = None
    profile_id: Optional[int] = None


class HoldingUpdate(BaseModel):
    avg_price: Optional[int] = None
    quantity: Optional[int] = None
    memo: Optional[str] = None
    profile_id: Optional[int] = None  # None = unassign when explicitly sent


def _derive_stock_type(output: dict) -> str:
    """KIS API output의 bstp_kor_isnm에서 종목 유형을 도출한다."""
    sector = (output.get("bstp_kor_isnm") or "").upper()
    if "ETF" in sector:
        return "ETF"
    if "ETN" in sector:
        return "ETN"
    if "리츠" in sector or "REIT" in sector:
        return "리츠"
    return "주식"


async def _fetch_current_prices(
    stock_codes: list[str],
) -> tuple[dict[str, dict], dict[str, str]]:
    """
    KIS API 실시간 조회로 현재가·등락률·섹터·종목유형을 반환한다.
    stock_recommendations 캐시를 사용하지 않아 항상 최신 데이터를 반환한다.
    반환: (prices, price_times)
      prices: {stock_code: {current_price, change_rate, sector_name, stock_type}}
      price_times: {stock_code: iso_datetime}
    """
    prices: dict[str, dict] = {}
    price_times: dict[str, str] = {}
    now_iso = datetime.now(timezone.utc).isoformat()

    async def _fetch_one(code: str) -> None:
        try:
            data = await kis_client.get_stock_price(code)
            out = data.get("output", {})
            cp = out.get("stck_prpr")
            cr = out.get("prdy_ctrt")
            prices[code] = {
                "current_price": int(cp) if cp else None,
                "change_rate": float(cr) if cr else None,
                "sector_name": out.get("bstp_kor_isnm") or None,
                "stock_type": _derive_stock_type(out),
            }
            price_times[code] = now_iso
        except Exception as e:
            logger.warning(f"{code} 현재가 조회 실패: {e}")
            prices[code] = {"current_price": None, "change_rate": None, "sector_name": None, "stock_type": None}

    await asyncio.gather(*[_fetch_one(c) for c in stock_codes], return_exceptions=True)
    return prices, price_times


def _enrich(holding: dict, prices: dict[str, dict], price_times: dict[str, str] | None = None) -> dict:
    """보유 종목에 현재가·손익 계산 필드를 추가."""
    code = holding["stock_code"]
    avg_price: int = holding["avg_price"]
    quantity: int = holding["quantity"]
    price_info = prices.get(code, {})

    current_price: Optional[int] = price_info.get("current_price")
    change_rate: Optional[float] = price_info.get("change_rate")
    sector_name: Optional[str] = price_info.get("sector_name")
    stock_type: Optional[str] = price_info.get("stock_type")

    purchase_amount = avg_price * quantity
    eval_amount = current_price * quantity if current_price else None
    profit_loss = (current_price - avg_price) * quantity if current_price else None
    profit_rate = (current_price - avg_price) / avg_price * 100 if current_price else None

    return {
        **holding,
        "current_price": current_price,
        "change_rate": change_rate,
        "sector_name": sector_name,
        "stock_type": stock_type,
        "price_updated_at": (price_times or {}).get(code),
        "purchase_amount": purchase_amount,
        "eval_amount": eval_amount,
        "profit_loss": profit_loss,
        "profit_rate": round(profit_rate, 2) if profit_rate is not None else None,
    }


@router.get("")
async def list_holdings(profile_id: Optional[int] = Query(None)):
    try:
        q = supabase.table("holdings").select("*").order("created_at")
        if profile_id is not None:
            q = q.eq("profile_id", profile_id)
        result = q.execute()
        rows: list[dict] = result.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not rows:
        return {"status": "success", "data": [], "summary": _empty_summary(), "price_fetched_at": None}

    codes = list({r["stock_code"] for r in rows})
    prices, price_times = await _fetch_current_prices(codes)

    # stock_master에서 KOSPI/KOSDAQ 시장 구분 조회
    market_map: dict[str, str] = {}
    try:
        mrows = supabase.table("stock_master").select("stock_code,market").in_("stock_code", codes).execute()
        market_map = {r["stock_code"]: r["market"] for r in (mrows.data or [])}
    except Exception:
        pass

    enriched = [_enrich(r, prices, price_times) for r in rows]
    for h in enriched:
        h["market"] = market_map.get(h["stock_code"])
    summary = _calc_summary(enriched)

    fetched_at = datetime.now(timezone.utc).isoformat()
    return {"status": "success", "data": enriched, "summary": summary, "price_fetched_at": fetched_at}


@router.post("")
async def create_holding(body: HoldingCreate):
    code = body.stock_code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="종목 코드를 입력해 주세요.")
    try:
        record = {
            "stock_code": code,
            "stock_name": body.stock_name.strip(),
            "avg_price": body.avg_price,
            "quantity": body.quantity,
        }
        if body.memo:
            record["memo"] = body.memo.strip()
        if body.profile_id is not None:
            record["profile_id"] = body.profile_id
        result = supabase.table("holdings").insert(record).execute()
        return {"status": "success", "data": result.data[0] if result.data else record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{holding_id}")
async def update_holding(holding_id: int, body: HoldingUpdate):
    updates: dict = {}
    if body.avg_price is not None:
        updates["avg_price"] = body.avg_price
    if body.quantity is not None:
        updates["quantity"] = body.quantity
    if body.memo is not None:
        updates["memo"] = body.memo
    if "profile_id" in body.model_fields_set:
        updates["profile_id"] = body.profile_id  # allows None (unassign)
    if not updates:
        raise HTTPException(status_code=400, detail="변경할 항목이 없습니다.")
    updates["updated_at"] = "now()"
    try:
        result = (
            supabase.table("holdings")
            .update(updates)
            .eq("id", holding_id)
            .execute()
        )
        return {"status": "success", "data": result.data[0] if result.data else {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{holding_id}/sell-analysis")
async def get_sell_analysis(holding_id: int):
    """보유 종목 매도 신호 분석 — 기술적·기본적·자산관리 관점 통합 점수 반환."""
    from app.services.sell_signal import analyze_sell
    from datetime import date, timedelta

    # 1. 보유 종목 조회
    try:
        row = supabase.table("holdings").select("*").eq("id", holding_id).limit(1).execute()
        if not row.data:
            raise HTTPException(status_code=404, detail="보유 종목을 찾을 수 없습니다.")
        holding = row.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    stock_code = holding["stock_code"]
    avg_price   = holding["avg_price"]
    quantity    = holding["quantity"]

    # 2. KIS API — 현재가 + OHLCV 병렬 조회
    today = date.today()
    start = (today - timedelta(days=130)).strftime("%Y%m%d")
    end   = today.strftime("%Y%m%d")

    try:
        price_data, ohlcv_data = await asyncio.gather(
            kis_client.get_stock_price(stock_code),
            kis_client.get_daily_ohlcv(stock_code, start, end),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시세 조회 실패: {e}")

    output  = price_data.get("output", {})
    records = list(reversed(ohlcv_data.get("output2", [])))

    def _flt(v):
        try:
            return float(v) if v and float(v) != 0 else None
        except (ValueError, TypeError):
            return None

    current_price = int(output["stck_prpr"]) if output.get("stck_prpr") else None
    per     = _flt(output.get("per"))
    pbr     = _flt(output.get("pbr"))
    eps     = _flt(output.get("eps"))
    w52_high = int(output["w52_hgpr"]) if output.get("w52_hgpr") else None

    # 3. 포트폴리오 비중 계산 (전체 보유 평가금액 대비)
    portfolio_weight: float | None = None
    try:
        all_rows = supabase.table("holdings").select("stock_code,avg_price,quantity").execute()
        codes = list({r["stock_code"] for r in (all_rows.data or [])})
        prices, _ = await _fetch_current_prices(codes)

        total_eval = sum(
            prices.get(r["stock_code"], {}).get("current_price", 0) * r["quantity"]
            for r in (all_rows.data or [])
            if prices.get(r["stock_code"], {}).get("current_price")
        )
        if current_price and total_eval > 0:
            portfolio_weight = round(current_price * quantity / total_eval * 100, 1)
    except Exception:
        pass

    # 4. 매도 신호 분석
    result = analyze_sell(
        records=records,
        avg_price=avg_price,
        current_price=current_price,
        per=per,
        pbr=pbr,
        eps=eps,
        w52_high=w52_high,
        portfolio_weight=portfolio_weight,
    )
    result["portfolio_weight"] = portfolio_weight
    result["current_price"] = current_price

    return {"status": "success", "data": result}


@router.delete("/{holding_id}")
async def delete_holding(holding_id: int):
    try:
        supabase.table("holdings").delete().eq("id", holding_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _empty_summary() -> dict:
    return {
        "total_purchase": 0,
        "total_eval": None,
        "total_profit_loss": None,
        "total_profit_rate": None,
    }


def _calc_summary(holdings: list[dict]) -> dict:
    total_purchase = sum(h["purchase_amount"] for h in holdings)

    items_with_price = [h for h in holdings if h["eval_amount"] is not None]
    if not items_with_price:
        return {
            "total_purchase": total_purchase,
            "total_eval": None,
            "total_profit_loss": None,
            "total_profit_rate": None,
        }

    total_eval = sum(h["eval_amount"] for h in items_with_price)
    # purchase_amount for items that have a current price
    partial_purchase = sum(h["purchase_amount"] for h in items_with_price)
    total_profit_loss = total_eval - partial_purchase
    total_profit_rate = total_profit_loss / partial_purchase * 100 if partial_purchase else None

    return {
        "total_purchase": total_purchase,
        "total_eval": total_eval,
        "total_profit_loss": total_profit_loss,
        "total_profit_rate": round(total_profit_rate, 2) if total_profit_rate is not None else None,
    }
