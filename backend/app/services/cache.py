import asyncio
import logging
import time
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

_MISSING = object()


class AsyncTTLCache:
    """TTL 캐시 + 단일 비행(single-flight) + 장애 시 만료 값 대체.

    - 같은 키로 동시에 들어온 요청은 로더를 한 번만 실행하고 결과(또는 예외)를 공유한다.
    - 로더가 실패하면 만료 후 stale_ttl 이내의 값을 대신 돌려준다.
    - max_size를 넘으면 가장 오래된 항목부터 버린다 (메모리 상한).
    - should_cache가 False를 돌려주는 값(빈 결과 등)은 저장하지 않는다.
    """

    def __init__(self, ttl: float, *, stale_ttl: float = 0.0, max_size: int = 512, clock=time.monotonic):
        self.ttl = ttl
        self.stale_ttl = stale_ttl
        self.max_size = max_size
        self._clock = clock
        self._data: dict[Any, tuple[float, Any]] = {}  # key -> (저장 시각, 값)
        self._inflight: dict[Any, asyncio.Future] = {}

    def _age_value(self, key):
        item = self._data.get(key)
        if item is None:
            return None, _MISSING
        stored_at, value = item
        return self._clock() - stored_at, value

    def peek(self, key):
        """TTL 이내의 값을 돌려주고, 없으면 None."""
        age, value = self._age_value(key)
        return value if age is not None and age < self.ttl else None

    def _store(self, key, value) -> None:
        if len(self._data) >= self.max_size and key not in self._data:
            horizon = self._clock() - (self.ttl + self.stale_ttl)
            for k in [k for k, (t, _) in self._data.items() if t < horizon]:
                del self._data[k]
            while len(self._data) >= self.max_size:
                del self._data[min(self._data, key=lambda k: self._data[k][0])]
        self._data[key] = (self._clock(), value)

    def invalidate(self, key=_MISSING) -> None:
        if key is _MISSING:
            self._data.clear()
        else:
            self._data.pop(key, None)

    def __len__(self) -> int:
        return len(self._data)

    async def get_or_load(
        self,
        key,
        loader: Callable[[], Awaitable[Any]],
        *,
        should_cache: Callable[[Any], bool] | None = None,
    ):
        age, value = self._age_value(key)
        if age is not None and age < self.ttl:
            return value

        fut = self._inflight.get(key)
        if fut is None:
            fut = asyncio.ensure_future(self._load(key, loader, should_cache))
            self._inflight[key] = fut

            def _cleanup(f: asyncio.Future, key=key) -> None:
                self._inflight.pop(key, None)
                if not f.cancelled():
                    f.exception()  # 아무도 기다리지 않아도 "never retrieved" 경고가 뜨지 않게 한다

            fut.add_done_callback(_cleanup)
        return await asyncio.shield(fut)

    async def _load(self, key, loader, should_cache):
        try:
            value = await loader()
        except Exception:
            age, stale = self._age_value(key)
            if age is not None and age < self.ttl + self.stale_ttl:
                logger.warning("캐시 로더 실패 — 만료된 값 사용 (key=%s, age=%.0fs)", key, age, exc_info=True)
                return stale
            raise
        if should_cache is None or should_cache(value):
            self._store(key, value)
        return value
