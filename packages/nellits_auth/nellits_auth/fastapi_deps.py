"""FastAPI dependencies that validate Nellits Accounts JWTs (cookie or Bearer)."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Annotated, Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "nellits_session")
ALGORITHM = "RS256"
DEFAULT_ISSUER = os.getenv("AUTH_ISSUER_URL", os.getenv("AUTH_ISSUER", "https://accounts.nellits.com"))
DEFAULT_JWKS = os.getenv(
    "AUTH_JWKS_URL",
    f"{DEFAULT_ISSUER.rstrip('/')}/.well-known/jwks.json",
)

bearer_scheme = HTTPBearer(auto_error=False)
cookie_scheme = APIKeyCookie(name=COOKIE_NAME, auto_error=False)

_jwks_cache: dict[str, Any] = {"fetched_at": 0.0, "keys": {}}
_JWKS_TTL_SECONDS = int(os.getenv("AUTH_JWKS_CACHE_SECONDS", "3600"))


@dataclass(frozen=True)
class NellitsUser:
    id: int
    email: str | None = None
    is_admin: bool = False


def _issuer() -> str:
    return os.getenv("AUTH_ISSUER_URL", os.getenv("AUTH_ISSUER", DEFAULT_ISSUER)).rstrip("/")


def _jwks_url() -> str:
    return os.getenv("AUTH_JWKS_URL", f"{_issuer()}/.well-known/jwks.json")


def _fetch_jwks(force: bool = False) -> dict[str, Any]:
    now = time.time()
    if not force and _jwks_cache["keys"] and (now - _jwks_cache["fetched_at"]) < _JWKS_TTL_SECONDS:
        return _jwks_cache["keys"]
    url = _jwks_url()
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        if _jwks_cache["keys"]:
            return _jwks_cache["keys"]
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to fetch JWKS from {url}",
        ) from e
    by_kid = {k["kid"]: k for k in data.get("keys", []) if "kid" in k}
    # Also index first key as default
    if not by_kid and data.get("keys"):
        by_kid["__default__"] = data["keys"][0]
    _jwks_cache["keys"] = by_kid
    _jwks_cache["fetched_at"] = now
    return by_kid


def _decode_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    kid = header.get("kid")
    keys = _fetch_jwks()
    jwk = keys.get(kid) if kid else None
    if jwk is None:
        keys = _fetch_jwks(force=True)
        jwk = keys.get(kid) or keys.get("__default__") or (next(iter(keys.values())) if keys else None)
    if jwk is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No matching signing key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return jwt.decode(
            token,
            jwk,
            algorithms=[ALGORITHM],
            issuer=_issuer(),
            options={"verify_aud": False},
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    cookie: Annotated[str | None, Depends(cookie_scheme)] = None,
) -> NellitsUser:
    token = None
    if creds and creds.credentials:
        token = creds.credentials
    elif cookie:
        token = cookie
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(token)
    try:
        uid = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from e
    return NellitsUser(
        id=uid,
        email=payload.get("email"),
        is_admin=bool(payload.get("is_admin")),
    )


def get_current_user_id(user: Annotated[NellitsUser, Depends(get_current_user)]) -> int:
    return user.id


def require_admin(user: Annotated[NellitsUser, Depends(get_current_user)]) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


CurrentUser = Annotated[NellitsUser, Depends(get_current_user)]
CurrentUserId = Annotated[int, Depends(get_current_user_id)]
