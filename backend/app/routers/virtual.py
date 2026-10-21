import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.errors import internal_error
from app.core.threads import run_blocking
from pydantic import BaseModel

from app.core.auth import verify_token
from app.services import virtual_trading as vt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/virtual", tags=["virtual"], dependencies=[Depends(verify_token)])


async def _fetch_realtime_prices(codes: list[str]) -> dict[str, int]:
    """보유 포지션 종목의 KIS 실시간가를 병렬 조회한다. 실패 종목은 결과에서 제외."""
    from app.services.market_data import get_price_data
    sem = asyncio.Semaphore(5)

    async def _fetch(code: str) -> tuple[str, int | None]:
        async with sem:
            try:
                data = await get_price_data(code)
                raw = data.get("output", {}).get("stck_prpr", "0")
                price = int(float(str(raw).replace(",", "") or "0"))
                return code, price if price > 0 else None
            except Exception as e:
                logger.warning(f"포지션 실시간가 조회 실패 {code}: {e}")
                return code, None

    results = await asyncio.gather(*[_fetch(c) for c in codes])
    return {c: p for c, p in results if p}


# ── 요청 스키마 ───────────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str = "가상 계좌"
    initial_cash: int = 10_000_000
    strategy: str = "both"
    min_score: int = 50
    max_score: Optional[int] = None
    score_filter_type: str = "gte"   # "gte" | "lte" | "range"
    max_positions: int = 5
    position_size: int = 20
    stop_loss_pct: int = 10
    take_profit_pct: int = 20
    profile_id: Optional[int] = None
    filter_excl_large_cap: bool = False
    filter_large_cap_threshold: Optional[int] = 50000
    filter_excl_high_amount: bool = False
    filter_high_amount_threshold: Optional[int] = 5000
    max_hold_days: Optional[int] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    strategy: Optional[str] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    score_filter_type: Optional[str] = None
    max_positions: Optional[int] = None
    position_size: Optional[int] = None
    stop_loss_pct: Optional[int] = None
    take_profit_pct: Optional[int] = None
    is_active: Optional[bool] = None
    filter_excl_large_cap: Optional[bool] = None
    filter_large_cap_threshold: Optional[int] = None
    filter_excl_high_amount: Optional[bool] = None
    filter_high_amount_threshold: Optional[int] = None
    max_hold_days: Optional[int] = None


class ManualTradeRequest(BaseModel):
    side: str           # 'buy' | 'sell'
    stock_code: str
    stock_name: str
    price: int
    quantity: Optional[int] = None


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _account_or_404(account_id: int) -> dict:
    account = vt.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="계좌를 찾을 수 없습니다.")
    return account


# ── 계좌 CRUD ─────────────────────────────────────────────────────────────────

@router.get("/accounts")
def list_accounts(profile_id: Optional[int] = Query(None)):
    try:
        return {"status": "success", "data": vt.list_accounts(profile_id)}
    except Exception as e:
        raise internal_error("가상 계좌 목록 조회에 실패했습니다.")


@router.post("/accounts")
def create_account(body: AccountCreate):
    try:
        account = vt.create_account(body.model_dump())
        return {"status": "success", "data": account}
    except Exception as e:
        raise internal_error("가상 계좌 생성에 실패했습니다.")


@router.patch("/accounts/{account_id}")
def update_account(account_id: int, body: AccountUpdate):
    _account_or_404(account_id)
    try:
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        account = vt.update_account(account_id, updates)
        return {"status": "success", "data": account}
    except Exception as e:
        raise internal_error("계좌 업데이트에 실패했습니다.")


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int):
    _account_or_404(account_id)
    try:
        vt.delete_account(account_id)
        return {"status": "success"}
    except Exception as e:
        raise internal_error("계좌 삭제에 실패했습니다.")


# ── 포지션 · 체결 내역 ─────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/positions")
async def get_positions(account_id: int):
    await run_blocking(_account_or_404, account_id)
    try:
        codes = await run_blocking(vt.get_position_codes, account_id)
        if not codes:
            return {"status": "success", "data": []}

        realtime_prices = await _fetch_realtime_prices(list(set(codes)))
        data = await run_blocking(vt.get_positions, account_id, realtime_prices or None)
        return {"status": "success", "data": data}
    except Exception as e:
        raise internal_error("포지션 조회에 실패했습니다.")


@router.get("/accounts/{account_id}/trades")
def get_trades(account_id: int, limit: int = Query(100, le=500)):
    _account_or_404(account_id)
    try:
        return {"status": "success", "data": vt.get_trades(account_id, limit)}
    except Exception as e:
        raise internal_error("거래 내역 조회에 실패했습니다.")


# ── 성과 지표 ─────────────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/performance")
async def get_performance(account_id: int):
    await run_blocking(_account_or_404, account_id)
    try:
        codes = await run_blocking(vt.get_position_codes, account_id)
        realtime_prices: dict[str, int] = {}
        if codes:
            realtime_prices = await _fetch_realtime_prices(list(set(codes)))

        data = await run_blocking(vt.get_performance, account_id, realtime_prices or None)
        if not data:
            raise HTTPException(status_code=404, detail="계좌를 찾을 수 없습니다.")
        return {"status": "success", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error("성과 조회에 실패했습니다.")


# ── 수동 체결 ─────────────────────────────────────────────────────────────────

@router.post("/accounts/{account_id}/trades")
def manual_trade(account_id: int, body: ManualTradeRequest):
    _account_or_404(account_id)
    if body.side not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="side는 'buy' 또는 'sell'이어야 합니다.")
    try:
        result = vt.manual_trade(
            account_id=account_id,
            side=body.side,
            stock_code=body.stock_code,
            stock_name=body.stock_name,
            price=body.price,
            quantity=body.quantity,
        )
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise internal_error("수동 체결에 실패했습니다.")
