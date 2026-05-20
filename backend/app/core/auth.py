import jwt
import httpx
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import ECAlgorithm

from app.core.config import settings

_security = HTTPBearer()

_jwks_cache: dict | None = None


def _get_public_key(kid: str):
    global _jwks_cache
    if _jwks_cache is None:
        resp = httpx.get(
            f"{settings.supabase_url}/auth/v1/.well-known/jwks.json",
            timeout=5,
        )
        resp.raise_for_status()
        _jwks_cache = {k["kid"]: k for k in resp.json().get("keys", [])}

    jwk = _jwks_cache.get(kid)
    if not jwk:
        raise HTTPException(status_code=401, detail="Unknown key id")
    return ECAlgorithm.from_jwk(jwk)


def verify_token(credentials: HTTPAuthorizationCredentials = Security(_security)) -> dict:
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        if alg == "ES256":
            key = _get_public_key(header["kid"])
        else:
            key = settings.supabase_jwt_secret

        return jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
