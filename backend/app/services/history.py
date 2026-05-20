"""
추천 종목 히스토리 저장/조회.

저장 정책:
  daily   — 매일 상위 10종목 스냅샷, 최근 7일 보관
  weekly  — 해당 주 일별 스냅샷의 출현 빈도 집계 → 상위 10종목, 최근 4주 보관
  monthly — 해당 월 일별 스냅샷의 출현 빈도 집계 → 상위 10종목, 최근 6개월 보관
"""
import logging
from collections import Counter
from datetime import date, timedelta

from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

_TABLE = "recommendation_history"
_TOP_N = 10
_MAX_DAILY = 7
_MAX_WEEKLY = 4
_MAX_MONTHLY = 6


# ── Period key helpers ────────────────────────────────────────────────────────

def _daily_key(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _weekly_key(d: date) -> str:
    return d.strftime("%G-W%V")   # ISO year + zero-padded week (01-53)


def _monthly_key(d: date) -> str:
    return d.strftime("%Y-%m")


def _cutoff_monthly(today: date, n_months: int) -> str:
    y, m = today.year, today.month - n_months
    while m <= 0:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


# ── Aggregation ───────────────────────────────────────────────────────────────

def _aggregate(rows: list[dict], fallback: list[dict]) -> list[dict]:
    """Frequency-rank stocks across daily rows; fall back to today's list."""
    if not rows:
        return fallback[:_TOP_N]
    counter: Counter = Counter()
    latest: dict[str, dict] = {}
    for row in rows:
        for stock in row.get("stocks", []):
            code = stock["stock_code"]
            counter[code] += 1
            latest[code] = stock
    return [latest[code] for code, _ in counter.most_common(_TOP_N)]


# ── Public API ────────────────────────────────────────────────────────────────

def save_snapshot(stocks: list[dict]) -> None:
    """
    stocks: 오늘의 추천 종목 리스트 (update_recommendations() 반환값).
    daily / weekly / monthly 세 가지 period_type으로 upsert 후 오래된 행 삭제.
    """
    today = date.today()
    top_today = stocks[:_TOP_N]

    try:
        # ── daily ─────────────────────────────────────────────────────────────
        daily_key = _daily_key(today)
        supabase.table(_TABLE).upsert(
            {"period_type": "daily", "period_key": daily_key, "stocks": top_today},
            on_conflict="period_type,period_key",
        ).execute()

        cutoff = _daily_key(today - timedelta(days=_MAX_DAILY))
        supabase.table(_TABLE).delete().eq("period_type", "daily").lt("period_key", cutoff).execute()

        # ── weekly ────────────────────────────────────────────────────────────
        week_start = _daily_key(today - timedelta(days=today.weekday()))
        daily_this_week = (
            supabase.table(_TABLE)
            .select("stocks")
            .eq("period_type", "daily")
            .gte("period_key", week_start)
            .execute()
            .data or []
        )
        week_key = _weekly_key(today)
        supabase.table(_TABLE).upsert(
            {"period_type": "weekly", "period_key": week_key,
             "stocks": _aggregate(daily_this_week, top_today)},
            on_conflict="period_type,period_key",
        ).execute()

        cutoff_w = _weekly_key(today - timedelta(weeks=_MAX_WEEKLY))
        supabase.table(_TABLE).delete().eq("period_type", "weekly").lt("period_key", cutoff_w).execute()

        # ── monthly ───────────────────────────────────────────────────────────
        month_start = _daily_key(today.replace(day=1))
        daily_this_month = (
            supabase.table(_TABLE)
            .select("stocks")
            .eq("period_type", "daily")
            .gte("period_key", month_start)
            .execute()
            .data or []
        )
        month_key = _monthly_key(today)
        supabase.table(_TABLE).upsert(
            {"period_type": "monthly", "period_key": month_key,
             "stocks": _aggregate(daily_this_month, top_today)},
            on_conflict="period_type,period_key",
        ).execute()

        cutoff_m = _cutoff_monthly(today, _MAX_MONTHLY)
        supabase.table(_TABLE).delete().eq("period_type", "monthly").lt("period_key", cutoff_m).execute()

        logger.info(f"히스토리 저장: daily={daily_key}, weekly={week_key}, monthly={month_key}")

    except Exception as e:
        logger.error(f"히스토리 저장 실패: {e}")


def get_history(period_type: str) -> list[dict]:
    """최신순으로 period_type에 해당하는 히스토리 반환."""
    limit = {"daily": _MAX_DAILY, "weekly": _MAX_WEEKLY, "monthly": _MAX_MONTHLY}.get(period_type, 10)
    result = (
        supabase.table(_TABLE)
        .select("period_key, stocks, created_at")
        .eq("period_type", period_type)
        .order("period_key", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []
