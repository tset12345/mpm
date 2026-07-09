import time

import jwt
import httpx
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import ECAlgorithm

from app.core.config import settings

_security = HTTPBearer()

_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL = 3600  # 1시간마다 재조회


def _get_public_key(kid: str):
    global _jwks_cache, _jwks_fetched_at
    if _jwks_cache is None or time.time() - _jwks_fetched_at > _JWKS_TTL:
        resp = httpx.get(
            f"{settings.supabase_url}/auth/v1/.well-known/jwks.json",
            timeout=5,
        )
        resp.raise_for_status()
        _jwks_cache = {k["kid"]: k for k in resp.json().get("keys", [])}
        _jwks_fetched_at = time.time()

    jwk = _jwks_cache.get(kid)
    if not jwk:
        # 캐시 미스 시 즉시 재조회 1회 허용
        _jwks_cache = None
        raise HTTPException(status_code=401, detail="Unknown key id")
    return ECAlgorithm.from_jwk(jwk)


def verify_token(credentials: HTTPAuthorizationCredentials = Security(_security)) -> dict:
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        # alg를 헤더에서 읽지 않고 kid 존재 여부로 분기 (algorithm confusion 방지)
        if kid:
            key = _get_public_key(kid)
            algorithms = ["ES256"]
        else:
            key = settings.supabase_jwt_secret
            algorithms = ["HS256"]

        payload = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 단일 사용자 화이트리스트 — ALLOWED_USER_EMAIL 설정 시 해당 계정만 허용
    if settings.allowed_user_email:
        if payload.get("email") != settings.allowed_user_email:
            raise HTTPException(status_code=403, detail="Forbidden")

    return payload
