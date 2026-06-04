import logging
from datetime import date, datetime, timezone, timedelta
from math import floor

from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


def _today() -> date:
    return datetime.now(KST).date()


# ── 계좌 ─────────────────────────────────────────────────────────────────────

def list_accounts(profile_id: int | None = None) -> list[dict]:
    q = supabase.table("virtual_accounts").select("*").order("created_at")
    if profile_id is not None:
        q = q.eq("profile_id", profile_id)
    return q.execute().data or []


def create_account(data: dict) -> dict:
    initial = data.get("initial_cash", 10_000_000)
    record = {
        "name":            data.get("name", "가상 계좌"),
        "initial_cash":    initial,
        "current_cash":    initial,
        "strategy":        data.get("strategy", "both"),
        "min_score":       data.get("min_score", 50),
        "max_positions":   data.get("max_positions", 5),
        "position_size":   data.get("position_size", 20),
        "stop_loss_pct":   data.get("stop_loss_pct", 10),
        "take_profit_pct": data.get("take_profit_pct", 20),
        "is_active":       True,
    }
    if data.get("profile_id") is not None:
        record["profile_id"] = data["profile_id"]
    res = supabase.table("virtual_accounts").insert(record).execute()
    return res.data[0]


def update_account(account_id: int, data: dict) -> dict:
    allowed = {"name", "strategy", "min_score", "max_positions",
               "position_size", "stop_loss_pct", "take_profit_pct", "is_active"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return get_account(account_id)
    res = supabase.table("virtual_accounts").update(updates).eq("id", account_id).execute()
    return res.data[0] if res.data else {}


def delete_account(account_id: int) -> None:
    supabase.table("virtual_accounts").delete().eq("id", account_id).execute()


def get_account(account_id: int) -> dict | None:
    res = supabase.table("virtual_accounts").select("*").eq("id", account_id).limit(1).execute()
    return res.data[0] if res.data else None


# ── 포지션 ────────────────────────────────────────────────────────────────────

def get_positions(account_id: int) -> list[dict]:
    res = supabase.table("virtual_positions").select("*").eq("account_id", account_id).order("entry_date").execute()
    positions = res.data or []

    # 현재가 보완: ① stock_recommendations → ② stock_ohlcv 폴백
    if positions:
        codes = [p["stock_code"] for p in positions]
        price_map: dict[str, int] = {}
        price_date_map: dict[str, str] = {}
        try:
            # ① 추천 테이블 (오늘 추천에 포함된 종목)
            latest_date_res = supabase.table("stock_recommendations").select("date").order("date", desc=True).limit(1).execute()
            if latest_date_res.data:
                latest_date = latest_date_res.data[0]["date"]
                price_res = supabase.table("stock_recommendations").select("stock_code,current_price").eq("date", latest_date).in_("stock_code", codes).execute()
                for r in (price_res.data or []):
                    if r.get("current_price"):
                        price_map[r["stock_code"]] = r["current_price"]
                        price_date_map[r["stock_code"]] = latest_date

            # ② OHLCV 폴백 — 추천 테이블에 없는 종목
            missing = [c for c in codes if c not in price_map]
            if missing:
                for code in missing:
                    ohlcv_res = (supabase.table("stock_ohlcv")
                                 .select("trade_date,close_price")
                                 .eq("stock_code", code)
                                 .order("trade_date", desc=True)
                                 .limit(1)
                                 .execute())
                    if ohlcv_res.data:
                        row = ohlcv_res.data[0]
                        price_map[code] = int(row["close_price"])
                        price_date_map[code] = row["trade_date"]

            for p in positions:
                cp = price_map.get(p["stock_code"])
                pd = price_date_map.get(p["stock_code"])
                p["current_price"] = cp
                if cp:
                    p["profit_loss"] = (cp - p["avg_price"]) * p["quantity"]
                    p["profit_rate"] = round((cp - p["avg_price"]) / p["avg_price"] * 100, 2)
                    p["hold_days"] = (date.fromisoformat(pd) - date.fromisoformat(p["entry_date"])).days if pd else None
                else:
                    p["profit_loss"] = None
                    p["profit_rate"] = None
                    p["hold_days"] = None
        except Exception as e:
            logger.warning(f"포지션 현재가 보완 실패: {e}")
            for p in positions:
                p["current_price"] = None
                p["profit_loss"] = None
                p["profit_rate"] = None
                p["hold_days"] = None

    return positions


def get_trades(account_id: int, limit: int = 100) -> list[dict]:
    res = (supabase.table("virtual_trades")
           .select("*")
           .eq("account_id", account_id)
           .order("traded_at", desc=True)
           .order("created_at", desc=True)
           .limit(limit)
           .execute())
    return res.data or []


# ── 성과 지표 ─────────────────────────────────────────────────────────────────

def get_performance(account_id: int) -> dict:
    account = get_account(account_id)
    if not account:
        return {}

    positions = get_positions(account_id)
    trades = get_trades(account_id, limit=1000)

    initial_cash = account["initial_cash"]
    current_cash = account["current_cash"]

    position_value = sum(
        (p.get("current_price") or p["avg_price"]) * p["quantity"]
        for p in positions
    )
    total_value = current_cash + position_value
    total_return_rate = round((total_value - initial_cash) / initial_cash * 100, 2)

    sell_trades = [t for t in trades if t["side"] == "sell"]
    realized_pnl = sum(t.get("pnl") or 0 for t in sell_trades)
    unrealized_pnl = sum(p.get("profit_loss") or 0 for p in positions)

    wins = [t for t in sell_trades if (t.get("pnl") or 0) > 0]
    win_rate = round(len(wins) / len(sell_trades) * 100, 1) if sell_trades else None

    # 최대 낙폭: 일별 total_value 추적은 미구현 — trade 기반 근사
    drawdown = None
    if sell_trades:
        losses = [t.get("pnl_rate") or 0 for t in sell_trades if (t.get("pnl") or 0) < 0]
        drawdown = round(min(losses), 2) if losses else 0.0

    avg_hold_days = None
    if sell_trades:
        days_list = []
        for t in sell_trades:
            buy = next((b for b in trades if b["side"] == "buy" and b["stock_code"] == t["stock_code"] and b["traded_at"] <= t["traded_at"]), None)
            if buy:
                d = (date.fromisoformat(t["traded_at"]) - date.fromisoformat(buy["traded_at"])).days
                days_list.append(d)
        avg_hold_days = round(sum(days_list) / len(days_list), 1) if days_list else None

    return {
        "initial_cash":      initial_cash,
        "current_cash":      current_cash,
        "position_value":    position_value,
        "total_value":       total_value,
        "total_return_rate": total_return_rate,
        "realized_pnl":      realized_pnl,
        "unrealized_pnl":    unrealized_pnl,
        "win_rate":          win_rate,
        "trade_count":       len(trades),
        "sell_count":        len(sell_trades),
        "avg_hold_days":     avg_hold_days,
        "max_drawdown":      drawdown,
    }


# ── 체결 ─────────────────────────────────────────────────────────────────────

def _execute_buy(account: dict, stock_code: str, stock_name: str,
                 price: int, trigger_type: str, engine: str | None,
                 tech_score: int | None) -> dict | None:
    account_id   = account["id"]
    current_cash = account["current_cash"]
    position_size = account["position_size"]

    invest_amount = floor(current_cash * position_size / 100)
    quantity = floor(invest_amount / price)
    if quantity <= 0:
        logger.info(f"[{account_id}] {stock_code} 매수 스킵 — 수량 0")
        return None

    amount = quantity * price
    today_str = _today().isoformat()

    supabase.table("virtual_trades").insert({
        "account_id":   account_id,
        "stock_code":   stock_code,
        "stock_name":   stock_name,
        "side":         "buy",
        "quantity":     quantity,
        "price":        price,
        "amount":       amount,
        "trigger_type": trigger_type,
        "engine":       engine,
        "tech_score":   tech_score,
        "traded_at":    today_str,
    }).execute()

    supabase.table("virtual_positions").upsert({
        "account_id":  account_id,
        "stock_code":  stock_code,
        "stock_name":  stock_name,
        "quantity":    quantity,
        "avg_price":   price,
        "entry_date":  today_str,
        "entry_score": tech_score,
        "engine":      engine,
    }, on_conflict="account_id,stock_code").execute()

    supabase.table("virtual_accounts").update({"current_cash": current_cash - amount}).eq("id", account_id).execute()

    logger.info(f"[{account_id}] {stock_code} 매수 체결 {quantity}주 @{price:,} ({trigger_type})")
    return {"stock_code": stock_code, "quantity": quantity, "price": price, "amount": amount}


def _execute_sell(account: dict, position: dict, price: int,
                  trigger_type: str, sell_score: int | None) -> dict | None:
    account_id   = account["id"]
    current_cash = account["current_cash"]
    stock_code   = position["stock_code"]
    quantity     = position["quantity"]
    avg_price    = position["avg_price"]

    amount   = quantity * price
    pnl      = (price - avg_price) * quantity
    pnl_rate = round((price - avg_price) / avg_price * 100, 2)
    today_str = _today().isoformat()

    supabase.table("virtual_trades").insert({
        "account_id":   account_id,
        "stock_code":   stock_code,
        "stock_name":   position["stock_name"],
        "side":         "sell",
        "quantity":     quantity,
        "price":        price,
        "amount":       amount,
        "trigger_type": trigger_type,
        "engine":       position.get("engine"),
        "sell_score":   sell_score,
        "pnl":          pnl,
        "pnl_rate":     pnl_rate,
        "traded_at":    today_str,
    }).execute()

    supabase.table("virtual_positions").delete().eq("id", position["id"]).execute()
    supabase.table("virtual_accounts").update({"current_cash": current_cash + amount}).eq("id", account_id).execute()

    logger.info(f"[{account_id}] {stock_code} 매도 체결 {quantity}주 @{price:,} 손익 {pnl:+,}원 ({trigger_type})")
    return {"stock_code": stock_code, "quantity": quantity, "price": price, "pnl": pnl}


# ── 알고리즘 트리거 ───────────────────────────────────────────────────────────

def virtual_buy_trigger(recommendations: list[dict]) -> None:
    """update_recommendations() 완료 후 호출 — 조건 충족 종목 자동 매수."""
    if not recommendations:
        return

    accounts = [a for a in list_accounts() if a["is_active"]]
    if not accounts:
        return

    for account in accounts:
        try:
            _process_buy_for_account(account, recommendations)
        except Exception as e:
            logger.error(f"[{account['id']}] 매수 트리거 오류: {e}")


def _process_buy_for_account(account: dict, recommendations: list[dict]) -> None:
    positions_res = supabase.table("virtual_positions").select("stock_code").eq("account_id", account["id"]).execute()
    held_codes = {p["stock_code"] for p in (positions_res.data or [])}

    # 당일 손절된 종목은 재매수 금지
    today_str = _today().isoformat()
    stoploss_res = (supabase.table("virtual_trades")
                   .select("stock_code")
                   .eq("account_id", account["id"])
                   .eq("trigger_type", "stop_loss")
                   .eq("traded_at", today_str)
                   .execute())
    held_codes |= {r["stock_code"] for r in (stoploss_res.data or [])}
    current_positions = len(held_codes)

    strategy    = account["strategy"]
    min_score   = account["min_score"]
    max_pos     = account["max_positions"]

    for rec in recommendations:
        if current_positions >= max_pos:
            break
        code  = rec["stock_code"]
        if code in held_codes:
            continue

        score   = rec.get("tech_score") or rec.get("total_score") or 0
        tags    = rec.get("tags") or []
        eng_a   = rec.get("engine_a_score") or 0
        eng_b   = rec.get("engine_b_score") or 0

        if score < min_score:
            continue

        # 전략 필터
        engine = None
        if strategy == "engine_a":
            if eng_a <= 0:
                continue
            engine = "A"
        elif strategy == "engine_b":
            if eng_b <= 0:
                continue
            engine = "B"
        else:  # both
            if "추세 돌파형" in tags:
                engine = "A"
            elif "역추세 반등형" in tags:
                engine = "B"

        price = rec.get("current_price")
        if not price or price <= 0:
            continue

        result = _execute_buy(account, code, rec.get("stock_name", ""), price, "algo_buy", engine, score)
        if result:
            held_codes.add(code)
            current_positions += 1
            # 계좌 잔액 갱신 (루프 내 재조회 방지)
            account["current_cash"] -= result["amount"]


def virtual_sell_trigger(price_map: dict[str, int] | None = None) -> None:
    """손절·익절·매도신호 자동 체결. price_map이 주어지면 DB 조회 없이 사용."""
    accounts = [a for a in list_accounts() if a["is_active"]]
    if not accounts:
        return

    if price_map is None:
        # 기본: DB에서 최신 추천가 조회
        price_map = {}
        try:
            latest_res = supabase.table("stock_recommendations").select("date").order("date", desc=True).limit(1).execute()
            if latest_res.data:
                latest_date = latest_res.data[0]["date"]
                rows = supabase.table("stock_recommendations").select("stock_code,current_price").eq("date", latest_date).execute()
                price_map = {r["stock_code"]: r["current_price"] for r in (rows.data or []) if r.get("current_price")}
        except Exception as e:
            logger.warning(f"매도 트리거 가격 조회 실패: {e}")
            return

    for account in accounts:
        try:
            _process_sell_for_account(account, price_map)
        except Exception as e:
            logger.error(f"[{account['id']}] 매도 트리거 오류: {e}")


def _process_sell_for_account(account: dict, price_map: dict[str, int]) -> None:
    from app.services.sell_signal import analyze_sell

    positions = get_positions(account["id"])
    stop_loss_pct   = account["stop_loss_pct"]
    take_profit_pct = account["take_profit_pct"]

    for pos in positions:
        code      = pos["stock_code"]
        avg_price = pos["avg_price"]
        price     = price_map.get(code)
        if not price:
            continue

        change_rate = (price - avg_price) / avg_price * 100

        # 손절
        if change_rate <= -stop_loss_pct:
            account = get_account(account["id"])
            _execute_sell(account, pos, price, "stop_loss", None)
            continue

        # 익절
        if change_rate >= take_profit_pct:
            account = get_account(account["id"])
            _execute_sell(account, pos, price, "take_profit", None)
            continue

        # 매도 신호 (OHLCV 없이 간이 분석)
        try:
            ohlcv_res = (supabase.table("stock_ohlcv")
                         .select("close_price,high_price,low_price,volume,trade_date")
                         .eq("stock_code", code)
                         .order("trade_date", desc=True)
                         .limit(60)
                         .execute())
            records = list(reversed(ohlcv_res.data or []))
            if len(records) < 20:
                continue

            fmt = [{"stck_clpr": str(r["close_price"]), "stck_hgpr": str(r["high_price"]),
                    "stck_lwpr": str(r["low_price"]), "acml_vol": str(r["volume"])} for r in records]
            result = analyze_sell(records=fmt, avg_price=avg_price, current_price=price)
            sell_score = result.get("sell_score", 0)

            if sell_score > 65:
                account = get_account(account["id"])
                _execute_sell(account, pos, price, "sell_signal", sell_score)
        except Exception as e:
            logger.warning(f"[{account['id']}] {code} 매도 신호 분석 실패: {e}")


# ── 수동 체결 ─────────────────────────────────────────────────────────────────

def manual_trade(account_id: int, side: str, stock_code: str, stock_name: str,
                 price: int, quantity: int | None = None) -> dict:
    account = get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    if side == "buy":
        if quantity:
            amount = quantity * price
            if amount > account["current_cash"]:
                raise ValueError("잔액이 부족합니다.")
            supabase.table("virtual_trades").insert({
                "account_id": account_id, "stock_code": stock_code, "stock_name": stock_name,
                "side": "buy", "quantity": quantity, "price": price, "amount": amount,
                "trigger_type": "manual", "traded_at": _today().isoformat(),
            }).execute()
            supabase.table("virtual_positions").upsert({
                "account_id": account_id, "stock_code": stock_code, "stock_name": stock_name,
                "quantity": quantity, "avg_price": price, "entry_date": _today().isoformat(),
            }, on_conflict="account_id,stock_code").execute()
            supabase.table("virtual_accounts").update({"current_cash": account["current_cash"] - amount}).eq("id", account_id).execute()
            return {"side": "buy", "stock_code": stock_code, "quantity": quantity, "price": price, "amount": amount}
        else:
            result = _execute_buy(account, stock_code, stock_name, price, "manual", None, None)
            if not result:
                raise ValueError("매수 수량이 0입니다.")
            return result
    else:
        pos_res = supabase.table("virtual_positions").select("*").eq("account_id", account_id).eq("stock_code", stock_code).limit(1).execute()
        if not pos_res.data:
            raise ValueError("보유 포지션이 없습니다.")
        return _execute_sell(account, pos_res.data[0], price, "manual", None)
