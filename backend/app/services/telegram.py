import logging
from datetime import datetime, timezone, timedelta

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


async def send_message(text: str) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("텔레그램 설정 없음 (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)")
        return False
    url = _TELEGRAM_API.format(token=settings.telegram_bot_token)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={
                "chat_id": settings.telegram_chat_id,
                "text": text,
                "parse_mode": "HTML",
            })
            resp.raise_for_status()
            logger.info("텔레그램 메시지 전송 완료")
            return True
    except Exception as e:
        logger.error(f"텔레그램 전송 실패: {e}")
        return False


def _format_recommendations(stocks: list[dict]) -> str:
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST).strftime("%m/%d %H:%M")

    lines = [f"<b>📊 오늘의 추천 종목</b>  ({now} KST)\n"]
    for i, s in enumerate(stocks, 1):
        name    = s.get("stock_name", "")
        code    = s.get("stock_code", "")
        price   = s.get("current_price") or s.get("entry_price") or 0
        score   = s.get("tech_score") or s.get("total_score") or 0
        score_a = s.get("engine_a_score", 0)
        score_b = s.get("engine_b_score", 0)
        srcs    = s.get("source_conditions") or []
        tags    = s.get("tags") or []
        cr      = s.get("change_rate") or 0.0

        src_str  = "·".join(srcs) if srcs else "-"
        tag_str  = " ".join(f"#{t}" for t in tags) if tags else ""
        cr_sign  = "+" if cr >= 0 else ""
        price_fmt = f"{price:,}"

        lines.append(
            f"{i}. <b>{name}</b>({code})\n"
            f"   수급: {src_str}\n"
            f"   추천가: {price_fmt}원  ({cr_sign}{cr:.1f}%)\n"
            f"   점수: {score}점(A: {score_a}점, B: {score_b}점)  {tag_str}"
        )

    return "\n\n".join(lines)


async def send_recommendation_report(stocks: list[dict]) -> None:
    if not settings.enable_telegram:
        return
    if not stocks:
        return
    text = _format_recommendations(stocks)
    await send_message(text)


_TRIGGER_KO = {
    "algo_buy":          "알고리즘 매수",
    "stop_loss":         "손절",
    "take_profit":       "익절",
    "atr_hard_stop":     "ATR 하드스탑",
    "atr_trailing_stop": "ATR 트레일링",
    "rsi_exhaustion":    "RSI 소멸",
    "entry_low_breach":  "진입저점 이탈",
    "time_limit_stop":   "기간 초과 손실",
    "ma20_half_exit":    "MA20 분할 익절",
    "target_reached":    "목표가 도달",
    "max_hold_exit":     "최대 보유일 초과",
    "manual":            "수동",
}


def _format_virtual_buy(account: dict, stock_code: str, stock_name: str,
                         price: int, quantity: int, amount: int,
                         engine: str | None, tech_score: int | None,
                         cash_after: int) -> str:
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST).strftime("%m/%d %H:%M")
    eng = f"Engine {engine}" if engine else "-"
    score_str = f"{tech_score}점" if tech_score is not None else "-"
    return (
        f"<b>🟢 가상 매수 체결</b>  [{account['name']}]  ({now})\n\n"
        f"종목: <b>{stock_name}</b> ({stock_code})\n"
        f"엔진: {eng}  |  점수: {score_str}\n"
        f"가격: {price:,}원  ×  {quantity:,}주\n"
        f"체결금액: {amount:,}원\n\n"
        f"잔여현금: {cash_after:,}원"
    )


def _format_virtual_sell(account: dict, stock_name: str, stock_code: str,
                          price: int, quantity: int, pnl: int, pnl_rate: float,
                          trigger_type: str, cash_after: int) -> str:
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST).strftime("%m/%d %H:%M")
    trigger_ko = _TRIGGER_KO.get(trigger_type, trigger_type)
    pnl_sign  = "+" if pnl >= 0 else ""
    pnl_emoji = "📈" if pnl >= 0 else "📉"
    return (
        f"<b>{pnl_emoji} 가상 매도 체결</b>  [{account['name']}]  ({now})\n\n"
        f"종목: <b>{stock_name}</b> ({stock_code})\n"
        f"사유: {trigger_ko}\n"
        f"가격: {price:,}원  ×  {quantity:,}주\n"
        f"손익: {pnl_sign}{pnl:,}원  ({pnl_sign}{pnl_rate:.2f}%)\n\n"
        f"잔여현금: {cash_after:,}원"
    )


async def send_virtual_buy(account: dict, stock_code: str, stock_name: str,
                            price: int, quantity: int, amount: int,
                            engine: str | None, tech_score: int | None,
                            cash_after: int) -> None:
    if not settings.enable_telegram:
        return
    text = _format_virtual_buy(account, stock_code, stock_name, price, quantity,
                                amount, engine, tech_score, cash_after)
    await send_message(text)


async def send_virtual_sell(account: dict, stock_name: str, stock_code: str,
                             price: int, quantity: int, pnl: int, pnl_rate: float,
                             trigger_type: str, cash_after: int) -> None:
    if not settings.enable_telegram:
        return
    text = _format_virtual_sell(account, stock_name, stock_code, price, quantity,
                                 pnl, pnl_rate, trigger_type, cash_after)
    await send_message(text)
