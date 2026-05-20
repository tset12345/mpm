from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def run_daily_sync():
    """장 마감 후 실행: 추천 종목 업데이트 + OHLCV 동기화 + 히스토리 저장"""
    from app.services.recommendations import update_recommendations
    from app.services.ohlcv_sync import sync_ohlcv
    from app.services.history import save_snapshot
    logger.info("일일 데이터 동기화 시작")
    try:
        stocks = await update_recommendations()
        codes = [s["stock_code"] for s in stocks]
        await sync_ohlcv(codes)
        save_snapshot(stocks)
        logger.info("일일 데이터 동기화 완료")
    except Exception as e:
        logger.error(f"일일 동기화 실패: {e}")


async def startup_sync_if_needed():
    """서버 시작 시 오늘 추천 데이터가 없으면 즉시 동기화."""
    from app.services.supabase_client import supabase
    today = date.today().isoformat()
    try:
        result = supabase.table("stock_recommendations").select("stock_code").eq("date", today).limit(1).execute()
        if not result.data:
            logger.info(f"시작 체크: 오늘({today}) 추천 데이터 없음 → 즉시 동기화 실행")
            await run_daily_sync()
        else:
            logger.info(f"시작 체크: 오늘({today}) 추천 데이터 확인됨 ({len(result.data)}건)")
    except Exception as e:
        logger.warning(f"시작 체크 실패: {e}")


def start_scheduler():
    # 서버 재시작 시 오늘 데이터가 없으면 즉시 동기화 (1회성 트리거)
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
    scheduler.start()
    logger.info("스케줄러 시작 — 08:50 / 11:00 / 14:00 / 16:10 (월~금 KST, 1일 4회) | 시작 체크 활성")
