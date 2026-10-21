import threading
import time
from collections import deque

from fastapi import HTTPException, Request

from app.core.config import settings


class SlidingWindowLimiter:
    """키별 슬라이딩 윈도 호출 제한 (프로세스 메모리). 키 수에 상한을 두어 메모리가 무한히 늘지 않게 한다."""

    def __init__(self, max_keys: int = 20_000, clock=time.monotonic):
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()
        self._max_keys = max_keys
        self._clock = clock

    def hit(self, key: str, limit: int, window: float = 60.0) -> tuple[bool, int]:
        """호출을 기록한다. (허용 여부, 거부 시 재시도까지 남은 초)를 돌려준다."""
        now = self._clock()
        with self._lock:
            q = self._hits.get(key)
            if q is None:
                if len(self._hits) >= self._max_keys:
                    self._evict(now, window)
                q = self._hits[key] = deque()
            while q and now - q[0] >= window:
                q.popleft()
            if len(q) >= limit:
                return False, max(1, int(window - (now - q[0])) + 1)
            q.append(now)
            return True, 0

    def _evict(self, now: float, window: float) -> None:
        for k in [k for k, q in self._hits.items() if not q or now - q[-1] >= window]:
            del self._hits[k]
        if len(self._hits) >= self._max_keys:  # 전부 활성이면 가장 오래 조용한 키부터 제거
            oldest = sorted(self._hits, key=lambda k: self._hits[k][-1])[: self._max_keys // 10 or 1]
            for k in oldest:
                del self._hits[k]

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    """요청자 IP. TRUSTED_PROXY_HOPS가 0이면 소켓 상대방, N이면 X-Forwarded-For의 뒤에서 N번째 값.

    X-Forwarded-For의 앞쪽 값은 클라이언트가 위조할 수 있으므로 신뢰하는 프록시가 덧붙인 뒤쪽 값만 쓴다.
    """
    peer = request.client.host if request.client else "unknown"
    hops = settings.trusted_proxy_hops
    if hops <= 0:
        return peer
    parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    return parts[-hops] if len(parts) >= hops else peer


def _reject(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail=f"요청이 너무 많습니다. {retry_after}초 후 다시 시도하세요.",
        headers={"Retry-After": str(retry_after)},
    )


def ip_rate_limit(request: Request) -> None:
    """앱 전역: IP당 분당 요청 수 제한. 헬스체크는 제외한다."""
    if request.url.path == "/api/v1/health":
        return
    ok, retry = limiter.hit(f"ip:{client_ip(request)}", settings.rate_limit_ip_per_min)
    if not ok:
        raise _reject(retry)


def identity_key(request: Request, payload: dict) -> tuple[str, int]:
    """인증된 호출자의 (제한 키, 분당 한도). 게스트 키는 모두가 공유하므로 IP를 키에 포함한다."""
    sub = payload.get("sub")
    if sub == "guest":
        return f"guest:{client_ip(request)}", settings.rate_limit_guest_per_min
    if sub == "ampm-app":
        return "ampm", settings.rate_limit_user_per_min
    return f"user:{sub}", settings.rate_limit_user_per_min


def enforce_identity_limit(request: Request, payload: dict) -> None:
    key, limit = identity_key(request, payload)
    ok, retry = limiter.hit(key, limit)
    if not ok:
        raise _reject(retry)


def expensive_rate_limit(scope: str, per_minute: int | None = None, when=None):
    """비용이 큰 작업(KIS 대량 조회·Gemini 호출·수동 동기화)용 별도 한도 의존성을 만든다.

    when(request)이 주어지면 True일 때만 한도를 적용한다 (예: force=true 쿼리)."""
    from fastapi import Depends
    from app.core.auth import verify_token

    def dependency(request: Request, payload: dict = Depends(verify_token)) -> None:
        if when is not None and not when(request):
            return
        key, _ = identity_key(request, payload)
        limit = per_minute if per_minute is not None else settings.rate_limit_expensive_per_min
        ok, retry = limiter.hit(f"{scope}:{key}", limit)
        if not ok:
            raise _reject(retry)

    return dependency
