import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import verify_token
from app.services import virtual_trading as vt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/virtual", tags=["virtual"], dependencies=[Depends(verify_token)])


# ── 요청 스키마 ───────────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str = "가상 계좌"
    initial_cash: int = 10_000_000
    strategy: str = "both"
    min_score: int = 50
    max_positions: int = 5
    position_size: int = 20
    stop_loss_pct: int = 10
    take_profit_pct: int = 20
    profile_id: Optional[int] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    strategy: Optional[str] = None
    min_score: Optional[int] = None
    max_positions: Optional[int] = None
    position_size: Optional[int] = None
    stop_loss_pct: Optional[int] = None
    take_profit_pct: Optional[int] = None
    is_active: Optional[bool] = None


class ManualTradeRequest(BaseModel):
    side: str           # 'buy' | 'sell'
    stock_code: str
    stock_name: str
    price: int
    quantity: Optional[int] = None


# ── 계좌 CRUD ─────────────────────────────────────────────────────────────────

@router.get("/accounts")
def list_accounts(profile_id: Optional[int] = Query(None)):
    try:
        return {"status": "success", "data": vt.list_accounts(profile_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts")
def create_account(body: AccountCreate):
    try:
        account = vt.create_account(body.model_dump())
        return {"status": "success", "data": account}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/accounts/{account_id}")
def update_account(account_id: int, body: AccountUpdate):
    try:
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        account = vt.update_account(account_id, updates)
        return {"status": "success", "data": account}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int):
    try:
        vt.delete_account(account_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 포지션 · 체결 내역 ─────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/positions")
def get_positions(account_id: int):
    try:
        return {"status": "success", "data": vt.get_positions(account_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}/trades")
def get_trades(account_id: int, limit: int = Query(100, le=500)):
    try:
        return {"status": "success", "data": vt.get_trades(account_id, limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 성과 지표 ─────────────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/performance")
def get_performance(account_id: int):
    try:
        data = vt.get_performance(account_id)
        if not data:
            raise HTTPException(status_code=404, detail="계좌를 찾을 수 없습니다.")
        return {"status": "success", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 수동 체결 ─────────────────────────────────────────────────────────────────

@router.post("/accounts/{account_id}/trades")
def manual_trade(account_id: int, body: ManualTradeRequest):
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
        raise HTTPException(status_code=500, detail=str(e))
