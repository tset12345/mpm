"""KIS 시세 조회의 공용 캐시 계층.

사용자·화면마다 같은 종목을 반복 조회하면 KIS 호출이 접속자 수에 비례해 늘어난다.
여기서 짧게 캐시하고 동시 요청을 하나로 합쳐 호출량을 종목 수에 비례하도록 묶는다.
반환값은 여러 요청이 공유하므로 읽기 전용으로 다룬다.
트레이딩 트리거(scheduler)는 최신가가 필요하므로 이 캐시를 쓰지 않고 kis_client를 직접 호출한다.
"""
from app.services.cache import AsyncTTLCache
from app.services.kis_api import kis_client

_price_cache = AsyncTTLCache(ttl=10, stale_ttl=60, max_size=1024)
_ohlcv_cache = AsyncTTLCache(ttl=120, stale_ttl=900, max_size=512)


async def get_price_data(code: str) -> dict:
    """현재가 응답(inquire-price 전체). 10초 캐시."""
    return await _price_cache.get_or_load(
        code,
        lambda: kis_client.get_stock_price(code),
        should_cache=lambda v: bool(v and v.get("output")),
    )


async def get_ohlcv_data(code: str, start: str, end: str) -> dict:
    """일봉 응답(inquire-daily-itemchartprice 전체). 2분 캐시."""
    return await _ohlcv_cache.get_or_load(
        (code, start, end),
        lambda: kis_client.get_daily_ohlcv(code, start, end),
        should_cache=lambda v: bool(v and v.get("output2")),
    )
