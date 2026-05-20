import asyncio
import logging
from datetime import date, timedelta
from app.services.kis_api import kis_client
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)


async def sync_ohlcv(stock_codes: list[str] | None = None) -> dict:
    """
    주어진 종목 코드 목록의 일별 OHLCV 데이터를 KIS에서 가져와 stock_ohlcv 테이블에 upsert.
    stock_codes가 None이면 거래량 순위 상위 50종목을 자동으로 조회.
    종목 간 0.5초 딜레이 적용 (rate limit 방지).
    """
    if stock_codes is None:
        try:
            ranking_data = await kis_client.get_volume_ranking()
            output = ranking_data.get("output", [])
            stock_codes = [item.get("mksc_shrn_iscd", "") for item in output[:50] if item.get("mksc_shrn_iscd")]
        except Exception as e:
            logger.error(f"거래량 순위 조회 실패: {e}")
            raise

    today = date.today()
    start_date = (today - timedelta(days=365 * 2)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")

    total_rows = 0
    errors = []

    for i, code in enumerate(stock_codes):
        if i > 0:
            await asyncio.sleep(0.5)

        try:
            ohlcv_data = await kis_client.get_daily_ohlcv(code, start_date, end_date)
        except Exception as e:
            logger.warning(f"{code} OHLCV 조회 실패: {e}")
            errors.append({"stock_code": code, "error": str(e)})
            continue

        records = ohlcv_data.get("output2", [])
        if not records:
            logger.debug(f"{code} OHLCV 데이터 없음")
            continue

        rows = []
        for r in records:
            bsop_date = r.get("stck_bsop_date", "")
            if not bsop_date:
                continue
            try:
                rows.append({
                    "stock_code": code,
                    "trade_date": f"{bsop_date[:4]}-{bsop_date[4:6]}-{bsop_date[6:8]}",
                    "open_price": int(r.get("stck_oprc") or 0),
                    "high_price": int(r.get("stck_hgpr") or 0),
                    "low_price": int(r.get("stck_lwpr") or 0),
                    "close_price": int(r.get("stck_clpr") or 0),
                    "volume": int(r.get("acml_vol") or 0),
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"{code} {bsop_date} 파싱 오류: {e}")
                continue

        if not rows:
            continue

        try:
            supabase.table("stock_ohlcv").upsert(
                rows,
                on_conflict="stock_code,trade_date",
            ).execute()
            total_rows += len(rows)
            logger.debug(f"{code} OHLCV {len(rows)}건 저장")
        except Exception as e:
            logger.error(f"{code} OHLCV 저장 실패: {e}")
            errors.append({"stock_code": code, "error": str(e)})

    logger.info(f"OHLCV 동기화 완료 — {len(stock_codes)}개 종목, {total_rows}건 저장, 오류 {len(errors)}건")
    return {
        "synced_stocks": len(stock_codes),
        "total_rows": total_rows,
        "errors": errors,
    }
