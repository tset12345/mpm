from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

from app.core.timezone import today_kst

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def run_daily_sync():
    """장 마감 후 실행: 추천 종목 업데이트 + OHLCV 동기화 + 히스토리 저장 + 가상 거래 트리거"""
    from app.services.recommendations import update_recommendations
    from app.services.ohlcv_sync import sync_ohlcv
    from app.services.history import save_snapshot
    from app.services.virtual_trading import virtual_buy_trigger, virtual_sell_trigger
    logger.info("일일 데이터 동기화 시작")
    try:
        stocks = await update_recommendations()
        codes = [s["stock_code"] for s in stocks]
        await sync_ohlcv(codes)
        save_snapshot(stocks)
        virtual_sell_trigger()
        virtual_buy_trigger(stocks)
        logger.info("일일 데이터 동기화 완료")
    except Exception as e:
        logger.error(f"일일 동기화 실패: {e}")


async def run_intraday_trading():
    """장중 10분마다 실행 — KIS 실시간 가격으로 가상 매매 트리거 (09:00~15:20 KST)."""
    from datetime import datetime, timezone, timedelta
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)
    # 09:00~15:20 범위만 실행 (15:30 장마감 직전까지)
    in_market = (now.hour == 9 and now.minute >= 0) or \
                (10 <= now.hour <= 14) or \
                (now.hour == 15 and now.minute <= 20)
    if not in_market:
        logger.info(f"장중 트리거 스킵 — 시장외 시간 {now.strftime('%H:%M')} KST")
        return

    import asyncio
    from app.services.kis_api import kis_client
    from app.services.virtual_trading import list_accounts, virtual_sell_trigger, virtual_buy_trigger
    from app.services.supabase_client import supabase

    logger.info(f"장중 트레이딩 트리거 시작 ({now.strftime('%H:%M')} KST)")
    try:
        # 활성 계좌 없으면 스킵
        accounts = [a for a in list_accounts() if a["is_active"]]
        if not accounts:
            return

        # 포지션 종목 코드 수집
        pos_codes: set[str] = set()
        for acc in accounts:
            res = supabase.table("virtual_positions").select("stock_code").eq("account_id", acc["id"]).execute()
            pos_codes.update(p["stock_code"] for p in (res.data or []))

        # 오늘 추천 종목 로드
        today = today_kst().isoformat()
        rec_res = supabase.table("stock_recommendations").select("*").eq("date", today).execute()
        recs = rec_res.data or []
        rec_codes = {r["stock_code"] for r in recs}

        all_codes = pos_codes | rec_codes
        if not all_codes:
            logger.info("장중 트리거: 조회 대상 종목 없음")
            return

        # KIS API 실시간 가격 병렬 조회 (세마포어 5)
        _sem = asyncio.Semaphore(5)

        async def _fetch(code: str) -> tuple[str, int | None]:
            async with _sem:
                try:
                    data = await kis_client.get_stock_price(code)
                    raw = data.get("output", {}).get("stck_prpr", "0")
                    price = int(float(str(raw).replace(",", "") or "0"))
                    return code, price if price > 0 else None
                except Exception as e:
                    logger.warning(f"실시간 가격 조회 실패 {code}: {e}")
                    return code, None

        results = await asyncio.gather(*[_fetch(c) for c in all_codes])
        price_map: dict[str, int] = {c: p for c, p in results if p}
        logger.info(f"실시간 가격 조회: {len(price_map)}/{len(all_codes)}개 성공")

        # 추천 데이터에 실시간 가격 반영
        enriched_recs = [
            {**r, "current_price": price_map.get(r["stock_code"], r.get("current_price"))}
            for r in recs
        ]

        # 매도 → 매수 순서로 트리거 (실시간 price_map 사용)
        virtual_sell_trigger(price_map=price_map)
        virtual_buy_trigger(enriched_recs)
        logger.info("장중 트레이딩 트리거 완료")
    except Exception as e:
        logger.error(f"장중 트레이딩 트리거 실패: {e}")


async def run_sector_leader_refresh():
    """장 시작 직후 전체 섹터 주도주 DB 갱신 (1일 1회, 09:05 KST)."""
    from app.services.sector_leader import refresh_all_sectors
    try:
        await refresh_all_sectors()
    except Exception as e:
        logger.error(f"섹터 주도주 갱신 실패: {e}")


async def startup_sync_if_needed():
    """서버 시작 시 오늘(KST) 추천 데이터가 없으면 즉시 동기화."""
    from app.services.supabase_client import supabase
    today = today_kst().isoformat()
    try:
        result = supabase.table("stock_recommendations").select("stock_code").eq("date", today).limit(1).execute()
        if not result.data:
            logger.info(f"시작 체크: 오늘 KST({today}) 추천 데이터 없음 → 즉시 동기화 실행")
            await run_daily_sync()
        else:
            logger.info(f"시작 체크: 오늘 KST({today}) 추천 데이터 확인됨 ({len(result.data)}건)")
    except Exception as e:
        logger.warning(f"시작 체크 실패: {e}")


def start_scheduler():
    # 서버 시작 시 오늘(KST) 데이터가 없으면 즉시 동기화 (1회성)
    scheduler.add_job(
        startup_sync_if_needed,
        "date",
        id="startup_check",
        replace_existing=True,
    )
    _sync_jobs = [
        ("pre_market_sync",    8, 50,  "장전"),
        ("mid_morning_sync",  11,  0,  "오전 장중"),
        ("mid_afternoon_sync",14,  0,  "오후 장중"),
        ("post_market_sync",  16, 10,  "장후"),
    ]
    for job_id, hour, minute, label in _sync_jobs:
        scheduler.add_job(
            run_daily_sync,
            CronTrigger(hour=hour, minute=minute, day_of_week="mon-fri", timezone="Asia/Seoul"),
            id=job_id,
            replace_existing=True,
            misfire_grace_time=3600,
        )
    scheduler.add_job(
        run_sector_leader_refresh,
        CronTrigger(hour=9, minute=5, day_of_week="mon-fri", timezone="Asia/Seoul"),
        id="sector_leader_refresh",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    # 장중 10분 단위 가상 매매 트리거 (09:00~15:50 등록, 내부에서 15:20 이후 스킵)
    scheduler.add_job(
        run_intraday_trading,
        CronTrigger(minute="*/10", hour="9-15", day_of_week="mon-fri", timezone="Asia/Seoul"),
        id="intraday_trading",
        replace_existing=True,
        misfire_grace_time=120,
    )
    scheduler.start()
    logger.info("스케줄러 시작 — 08:50/11:00/14:00/16:10 전체동기화 | 09:05 섹터주도주 | 장중 10분 가상매매 (월~금 KST)")
