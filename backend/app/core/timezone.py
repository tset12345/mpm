from datetime import datetime, timezone, timedelta, date

KST = timezone(timedelta(hours=9))


def today_kst() -> date:
    """한국 표준시(KST, UTC+9) 기준 오늘 날짜."""
    return datetime.now(KST).date()


def now_kst() -> datetime:
    """한국 표준시(KST, UTC+9) 기준 현재 시각."""
    return datetime.now(KST)
