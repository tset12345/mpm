import logging
import time

from fastapi import APIRouter, Depends, Request

from app.core.auth import verify_token
from app.core.config import settings
from app.core.ratelimit import client_ip
from app.services.scheduler import scheduler
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/health", tags=["system"], dependencies=[Depends(verify_token)])

_STARTED_AT = time.time()


def _rss_mb() -> int | None:
    """현재 프로세스 상주 메모리(MB). Linux /proc 전용, 그 외 환경은 None."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    return None


def _latest(table: str, column: str) -> str | None:
    res = supabase.table(table).select(column).order(column, desc=True).limit(1).execute()
    return res.data[0][column] if res.data else None


@router.get("/detail")
def health_detail(request: Request):
    """인증 필요. DB 응답 속도, 데이터 최신성, 스케줄러 상태, 메모리를 한 번에 확인한다."""
    checks: dict = {}

    started = time.perf_counter()
    try:
        _latest("stock_recommendations", "date")
        checks["db"] = {"ok": True, "latency_ms": round((time.perf_counter() - started) * 1000)}
    except Exception:
        logger.exception("health_detail: DB 점검 실패")
        checks["db"] = {"ok": False}

    freshness: dict = {}
    if checks["db"]["ok"]:
        for key, table, column in (
            ("recommendations_date", "stock_recommendations", "date"),
            ("ohlcv_date", "stock_ohlcv", "trade_date"),
        ):
            try:
                freshness[key] = _latest(table, column)
            except Exception:
                logger.exception("health_detail: %s 조회 실패", key)
                freshness[key] = None

    return {
        "status": "ok" if checks["db"]["ok"] else "degraded",
        "version": request.app.version,
        "uptime_sec": round(time.time() - _STARTED_AT),
        "rss_mb": _rss_mb(),
        "checks": checks,
        "data_freshness": freshness,
        "client": {
            "peer": request.client.host if request.client else None,
            "x_forwarded_for": request.headers.get("x-forwarded-for"),
            "resolved_ip": client_ip(request),
            "trusted_proxy_hops": settings.trusted_proxy_hops,
        },
        "scheduler": {
            "enabled": settings.enable_scheduler or settings.enable_intraday,
            "running": scheduler.running,
            "jobs": len(scheduler.get_jobs()) if scheduler.running else 0,
        },
    }
