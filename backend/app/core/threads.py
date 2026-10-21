import asyncio


async def run_blocking(fn, /, *args, **kwargs):
    """동기 함수(Supabase 호출 등)를 스레드풀에서 실행해 이벤트 루프가 막히지 않게 한다.

    contextvars(요청 ID 등)는 to_thread가 복사해 준다.
    """
    return await asyncio.to_thread(fn, *args, **kwargs)
