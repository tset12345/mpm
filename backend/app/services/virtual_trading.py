import asyncio
import logging
from datetime import date, datetime, timezone, timedelta
from math import floor

from app.services.supabase_client import supabase
from app.services.technical import atr as calc_atr, sma, rsi

logger = logging.getLogger(__name__)


def _fire_telegram(coro) -> None:
    """실행 중인 이벤트 루프에 텔레그램 코루틴을 fire-and-forget으로 등록."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(coro)
        else:
            loop.run_until_complete(coro)
    except Exception as e:
        logger.debug(f"텔레그램 알림 등록 실패: {e}")

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
        "name":              data.get("name", "가상 계좌"),
        "initial_cash":      initial,
        "current_cash":      initial,
        "strategy":          data.get("strategy", "both"),
        "min_score":         data.get("min_score", 50),
        "max_score":         data.get("max_score", None),
        "score_filter_type": data.get("score_filter_type", "gte"),
        "max_positions":     data.get("max_positions", 5),
        "position_size":     data.get("position_size", 20),
        "stop_loss_pct":     data.get("stop_loss_pct", 10),
        "take_profit_pct":   data.get("take_profit_pct", 20),
        "is_active":                  True,
        "filter_excl_large_cap":      data.get("filter_excl_large_cap", False),
        "filter_large_cap_threshold": data.get("filter_large_cap_threshold", 50000),
        "filter_excl_high_amount":    data.get("filter_excl_high_amount", False),
        "filter_high_amount_threshold": data.get("filter_high_amount_threshold", 5000),
        "max_hold_days":              data.get("max_hold_days", None),
    }
    if data.get("profile_id") is not None:
        record["profile_id"] = data["profile_id"]
    res = supabase.table("virtual_accounts").insert(record).execute()
    return res.data[0]


def update_account(account_id: int, data: dict) -> dict:
    allowed = {"name", "strategy", "min_score", "max_score", "score_filter_type",
               "max_positions", "position_size", "stop_loss_pct", "take_profit_pct", "is_active",
               "filter_excl_large_cap", "filter_large_cap_threshold",
               "filter_excl_high_amount", "filter_high_amount_threshold",
               "max_hold_days"}
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

def get_positions(account_id: int,
                  realtime_prices: dict[str, int] | None = None) -> list[dict]:
    """포지션 조회.

    realtime_prices가 주어지면 해당 가격을 직접 사용한다.
    없으면 stock_recommendations → stock_ohlcv 순으로 DB 스냅샷을 폴백한다.
    """
    res = supabase.table("virtual_positions").select("*").eq("account_id", account_id).order("entry_date").execute()
    positions = res.data or []
    if not positions:
        return positions

    codes = [p["stock_code"] for p in positions]
    today_str = _today().isoformat()

    if realtime_prices is not None:
        # ── 실시간가 경로 (라우터에서 KIS 조회 후 전달)
        for p in positions:
            cp = realtime_prices.get(p["stock_code"])
            p["current_price"] = cp
            if cp:
                p["profit_loss"] = (cp - p["avg_price"]) * p["quantity"]
                p["profit_rate"] = round((cp - p["avg_price"]) / p["avg_price"] * 100, 2)
                p["hold_days"] = (date.fromisoformat(today_str) - date.fromisoformat(p["entry_date"])).days
            else:
                p["profit_loss"] = None
                p["profit_rate"] = None
                p["hold_days"] = None
        return positions

    # ── DB 스냅샷 경로 (실시간가 없을 때 폴백)
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

def get_performance(account_id: int,
                    realtime_prices: dict[str, int] | None = None) -> dict:
    account = get_account(account_id)
    if not account:
        return {}

    positions = get_positions(account_id, realtime_prices=realtime_prices)
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

def _fetch_ohlcv_for_exit(code: str, limit: int = 70) -> list[dict]:
    """매도 판단용 OHLCV 조회 (최신순 → 오름차순 반환)."""
    res = (supabase.table("stock_ohlcv")
           .select("close_price,high_price,low_price,volume,trade_date")
           .eq("stock_code", code)
           .order("trade_date", desc=True)
           .limit(limit)
           .execute())
    return list(reversed(res.data or []))


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

    # 매수 시점 ATR·저가 계산 (엔진별 청산 기준으로 저장)
    entry_atr: int | None = None
    entry_low: int | None = None
    try:
        records = _fetch_ohlcv_for_exit(stock_code, 70)
        if len(records) >= 15:
            closes  = [float(r["close_price"]) for r in records]
            highs   = [float(r["high_price"])  for r in records]
            lows    = [float(r["low_price"])   for r in records]
            atr_val = calc_atr(highs, lows, closes, 14)
            if atr_val is not None:
                entry_atr = int(atr_val)
            if records:
                entry_low = int(records[-1]["low_price"])
    except Exception as e:
        logger.debug(f"{stock_code} 매수 ATR 계산 실패: {e}")

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
        "account_id":    account_id,
        "stock_code":    stock_code,
        "stock_name":    stock_name,
        "quantity":      quantity,
        "avg_price":     price,
        "entry_date":    today_str,
        "entry_score":   tech_score,
        "engine":        engine,
        "entry_atr":     entry_atr,
        "highest_price": price,
        "half_exited":   False,
        "entry_low":     entry_low,
    }, on_conflict="account_id,stock_code").execute()

    cash_after = current_cash - amount
    supabase.table("virtual_accounts").update({"current_cash": cash_after}).eq("id", account_id).execute()

    logger.info(f"[{account_id}] {stock_code} 매수 체결 {quantity}주 @{price:,} ({trigger_type}) ATR={entry_atr}")

    from app.services.telegram import send_virtual_buy
    _fire_telegram(send_virtual_buy(
        account, stock_code, stock_name, price, quantity, amount,
        engine, tech_score, cash_after,
    ))

    return {"stock_code": stock_code, "quantity": quantity, "price": price, "amount": amount}


def _execute_sell(account: dict, position: dict, price: int,
                  trigger_type: str, sell_score: int | None,
                  quantity: int | None = None) -> dict | None:
    """전량 또는 지정 수량 매도. quantity 생략 시 보유 전량."""
    account_id   = account["id"]
    current_cash = account["current_cash"]
    stock_code   = position["stock_code"]
    pos_qty      = position["quantity"]
    avg_price    = position["avg_price"]
    sell_qty     = quantity if quantity is not None else pos_qty

    if sell_qty <= 0:
        return None

    amount   = sell_qty * price
    pnl      = (price - avg_price) * sell_qty
    pnl_rate = round((price - avg_price) / avg_price * 100, 2)
    today_str = _today().isoformat()

    supabase.table("virtual_trades").insert({
        "account_id":   account_id,
        "stock_code":   stock_code,
        "stock_name":   position["stock_name"],
        "side":         "sell",
        "quantity":     sell_qty,
        "price":        price,
        "amount":       amount,
        "trigger_type": trigger_type,
        "engine":       position.get("engine"),
        "sell_score":   sell_score,
        "pnl":          pnl,
        "pnl_rate":     pnl_rate,
        "traded_at":    today_str,
    }).execute()

    remaining = pos_qty - sell_qty
    if remaining <= 0:
        supabase.table("virtual_positions").delete().eq("id", position["id"]).execute()
    else:
        # 분할 매도: 수량 차감 + half_exited 플래그 설정
        supabase.table("virtual_positions").update({
            "quantity": remaining,
            "half_exited": True,
        }).eq("id", position["id"]).execute()

    cash_after = current_cash + amount
    supabase.table("virtual_accounts").update({"current_cash": cash_after}).eq("id", account_id).execute()

    logger.info(f"[{account_id}] {stock_code} 매도 체결 {sell_qty}주 @{price:,} 손익 {pnl:+,}원 ({trigger_type})")

    from app.services.telegram import send_virtual_sell
    _fire_telegram(send_virtual_sell(
        account, position["stock_name"], stock_code, price, sell_qty,
        pnl, pnl_rate, trigger_type, cash_after,
    ))

    return {"stock_code": stock_code, "quantity": sell_qty, "price": price, "pnl": pnl}


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

    strategy          = account["strategy"]
    min_score         = account["min_score"]
    max_score         = account.get("max_score")
    score_filter_type = account.get("score_filter_type", "gte")
    max_pos           = account["max_positions"]

    filter_excl_large_cap        = account.get("filter_excl_large_cap", False)
    filter_large_cap_threshold   = account.get("filter_large_cap_threshold") or 50000
    filter_excl_high_amount      = account.get("filter_excl_high_amount", False)
    filter_high_amount_threshold = account.get("filter_high_amount_threshold") or 5000

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

        if score_filter_type == "gte":
            if score < min_score:
                continue
        elif score_filter_type == "lte":
            if max_score is not None and score > max_score:
                continue
        elif score_filter_type == "range":
            if score < min_score or (max_score is not None and score > max_score):
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
        elif strategy == "both_and":
            # A·B 모두 양수일 때만 매수 — 점수 높은 엔진의 청산 전략 사용
            if eng_a <= 0 or eng_b <= 0:
                continue
            engine = "A" if eng_a >= eng_b else "B"
        else:  # both (OR)
            if "추세 돌파형" in tags:
                engine = "A"
            elif "역추세 반등형" in tags:
                engine = "B"

        # Engine B 종목 필터 (engine이 B로 결정된 경우만 적용)
        if engine == "B":
            mc = rec.get("market_cap_e8") or 0
            da = rec.get("daily_amount_e8") or 0
            if filter_excl_large_cap and mc > 0 and mc > filter_large_cap_threshold:
                logger.debug(f"[{account['id']}] {code} 시가총액 필터 제외 ({mc:,}억원 > {filter_large_cap_threshold:,}억원)")
                continue
            if filter_excl_high_amount and da > 0 and da > filter_high_amount_threshold:
                logger.debug(f"[{account['id']}] {code} 거래대금 필터 제외 ({da:,}억원 > {filter_high_amount_threshold:,}억원)")
                continue

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
    positions_res = supabase.table("virtual_positions").select("*").eq("account_id", account["id"]).execute()
    positions = positions_res.data or []
    stop_loss_pct   = account["stop_loss_pct"]
    take_profit_pct = account["take_profit_pct"]
    max_hold_days   = account.get("max_hold_days")
    today = _today()

    for pos in positions:
        code      = pos["stock_code"]
        avg_price = pos["avg_price"]
        price     = price_map.get(code)
        if not price:
            continue

        change_rate = (price - avg_price) / avg_price * 100
        engine      = pos.get("engine")

        # ── 공통: 고정 손절·익절 ────────────────────────────────────────────────
        if change_rate <= -stop_loss_pct:
            account = get_account(account["id"])
            _execute_sell(account, pos, price, "stop_loss", None)
            continue

        if change_rate >= take_profit_pct:
            account = get_account(account["id"])
            _execute_sell(account, pos, price, "take_profit", None)
            continue

        # ── 공통: 최대 보유일수 초과 ────────────────────────────────────────────
        if max_hold_days:
            entry_date_str = pos.get("entry_date", "")
            if entry_date_str:
                try:
                    hold_days = (today - date.fromisoformat(entry_date_str)).days
                    if hold_days >= max_hold_days:
                        account = get_account(account["id"])
                        _execute_sell(account, pos, price, "max_hold_exit", None)
                        continue
                except (ValueError, TypeError):
                    pass

        # ── OHLCV 조회 ─────────────────────────────────────────────────────────
        try:
            records = _fetch_ohlcv_for_exit(code, 70)
            if len(records) < 15:
                continue

            closes = [float(r["close_price"]) for r in records]
            highs  = [float(r["high_price"])  for r in records]
            lows   = [float(r["low_price"])   for r in records]

            atr_val = calc_atr(highs, lows, closes, 14)
            ma20    = sma(closes, 20)
        except Exception as e:
            logger.warning(f"[{account['id']}] {code} OHLCV 조회 실패: {e}")
            continue

        # ── Engine A 청산 ───────────────────────────────────────────────────────
        if engine == "A":
            entry_atr     = pos.get("entry_atr")
            highest_price = pos.get("highest_price") or avg_price

            # highest_price 갱신
            if price > highest_price:
                highest_price = price
                supabase.table("virtual_positions").update(
                    {"highest_price": price}
                ).eq("id", pos["id"]).execute()

            # ATR 하드 스탑: 진입가 - 1.5 × entry_atr
            if entry_atr and price < avg_price - 1.5 * entry_atr:
                account = get_account(account["id"])
                _execute_sell(account, pos, price, "atr_hard_stop", None)
                continue

            # ATR 트레일링 스탑: 최고가 - 2.0 × 현재 ATR
            if atr_val and price < highest_price - 2.0 * atr_val:
                account = get_account(account["id"])
                _execute_sell(account, pos, price, "atr_trailing_stop", None)
                continue

            # RSI 모멘텀 소멸: 70 위에서 70 아래로 하향
            if len(closes) >= 16:
                rsi_curr = rsi(closes, 14)
                rsi_prev = rsi(closes[:-1], 14)
                if (rsi_prev is not None and rsi_curr is not None
                        and rsi_prev > 70 and rsi_curr <= 70):
                    account = get_account(account["id"])
                    _execute_sell(account, pos, price, "rsi_exhaustion", None)
                    continue

        # ── Engine B 청산 ───────────────────────────────────────────────────────
        elif engine == "B":
            entry_date  = pos.get("entry_date", "")
            half_exited = pos.get("half_exited", False)
            entry_low   = pos.get("entry_low")

            holding_bars = 0
            if entry_date:
                try:
                    holding_bars = (today - date.fromisoformat(entry_date)).days
                except (ValueError, TypeError):
                    pass

            # 진입 저점 이탈 손절
            if entry_low and price < entry_low:
                account = get_account(account["id"])
                _execute_sell(account, pos, price, "entry_low_breach", None)
                continue

            # 보유 기간 초과 + 손실 → 기회비용 청산
            if holding_bars >= 5 and price <= avg_price:
                account = get_account(account["id"])
                _execute_sell(account, pos, price, "time_limit_stop", None)
                continue

            # MA20 첫 터치 → 분할 익절 (50%)
            if (not half_exited and ma20 is not None
                    and len(closes) >= 2 and closes[-2] < ma20 <= price):
                half_qty = max(1, pos["quantity"] // 2)
                account = get_account(account["id"])
                _execute_sell(account, pos, price, "ma20_half_exit", None, quantity=half_qty)
                continue

            # 이격도 ≥ 102% 또는 RSI ≥ 60 → 전량 익절
            disparity = price / ma20 * 100 if (ma20 and ma20 > 0) else 0
            rsi_val   = rsi(closes, 14)
            if disparity >= 102 or (rsi_val is not None and rsi_val >= 60):
                account = get_account(account["id"])
                _execute_sell(account, pos, price, "target_reached", None)
                continue


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
