"""Auth: RS256 JWT creation, JWKS, and current-user dependency."""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "accounts_session")
ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "30"))
ISSUER = os.getenv("AUTH_ISSUER", "http://localhost:8001")
COOKIE_DOMAIN = os.getenv("AUTH_COOKIE_DOMAIN", "")  # e.g. ".example.com"; empty for localhost
COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "true").lower() in ("1", "true", "yes")

bearer_scheme = HTTPBearer(auto_error=False)
cookie_scheme = APIKeyCookie(name=COOKIE_NAME, auto_error=False)


def hash_password(password: str) -> str:
    import bcrypt

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    import bcrypt

    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _b64url_uint(val: int) -> str:
    length = (val.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(val.to_bytes(length, "big")).rstrip(b"=").decode("ascii")


@lru_cache(maxsize=1)
def _load_keys() -> tuple[Any, Any, str]:
    """Return (private_key, public_key, kid). Keys from PEM env/files or generated for dev."""
    private_pem = os.getenv("AUTH_RSA_PRIVATE_KEY", "").strip()
    public_pem = os.getenv("AUTH_RSA_PUBLIC_KEY", "").strip()
    kid = os.getenv("AUTH_KEY_ID", "accounts-1")

    private_path = os.getenv("AUTH_RSA_PRIVATE_KEY_PATH", "").strip()
    public_path = os.getenv("AUTH_RSA_PUBLIC_KEY_PATH", "").strip()
    if private_path and Path(private_path).is_file():
        private_pem = Path(private_path).read_text()
    if public_path and Path(public_path).is_file():
        public_pem = Path(public_path).read_text()

    if private_pem:
        # Support escaped newlines in env vars
        private_pem = private_pem.replace("\\n", "\n")
        private_key = serialization.load_pem_private_key(private_pem.encode(), password=None)
        if public_pem:
            public_pem = public_pem.replace("\\n", "\n")
            public_key = serialization.load_pem_public_key(public_pem.encode())
        else:
            public_key = private_key.public_key()
        return private_key, public_key, kid

    # Dev fallback: ephemeral key (tokens invalidate on restart)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key, kid


def _private_pem() -> str:
    private_key, _, _ = _load_keys()
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _public_pem() -> str:
    _, public_key, _ = _load_keys()
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


def public_jwks() -> dict:
    """JWKS document for app services to validate tokens."""
    _, public_key, kid = _load_keys()
    numbers = public_key.public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": ALGORITHM,
                "kid": kid,
                "n": _b64url_uint(numbers.n),
                "e": _b64url_uint(numbers.e),
            }
        ]
    }


def create_access_token(
    user_id: int,
    *,
    email: str | None = None,
    is_admin: bool = False,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    _, _, kid = _load_keys()
    payload = {
        "sub": str(user_id),
        "iss": ISSUER,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "email": email,
        "is_admin": bool(is_admin),
    }
    return jwt.encode(
        payload,
        _private_pem(),
        algorithm=ALGORITHM,
        headers={"kid": kid},
    )


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            _public_pem(),
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={"verify_aud": False},
        )
        return payload
    except (JWTError, ValueError, TypeError):
        return None


def get_current_user_claims(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    cookie: Annotated[str | None, Depends(cookie_scheme)] = None,
) -> dict:
    """Resolve current user claims from Bearer token or session cookie."""
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
    payload = decode_access_token(token)
    if payload is None or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_user_id(
    claims: Annotated[dict, Depends(get_current_user_claims)],
) -> int:
    try:
        return int(claims["sub"])
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from e


CurrentUserId = Annotated[int, Depends(get_current_user_id)]
CurrentUserClaims = Annotated[dict, Depends(get_current_user_claims)]


def cookie_kwargs(max_age: int | None = None) -> dict:
    """Common Set-Cookie options for the shared session cookie."""
    kwargs: dict[str, Any] = {
        "key": COOKIE_NAME,
        "path": "/",
        "httponly": True,
        "samesite": "lax",
        "secure": COOKIE_SECURE,
    }
    if max_age is not None:
        kwargs["max_age"] = max_age
    if COOKIE_DOMAIN:
        kwargs["domain"] = COOKIE_DOMAIN
    return kwargs


def redirect_uri_allowed(redirect_uri: str) -> bool:
    """Allow redirects under AUTH_COOKIE_DOMAIN, localhost, or AUTH_REDIRECT_ALLOWLIST."""
    from urllib.parse import urlparse

    allowed_extra = [
        s.strip() for s in os.getenv("AUTH_REDIRECT_ALLOWLIST", "").split(",") if s.strip()
    ]
    try:
        parsed = urlparse(redirect_uri)
    except Exception:
        return False
    if not parsed.scheme or not parsed.netloc:
        return False
    host = parsed.hostname or ""
    if COOKIE_DOMAIN:
        root = COOKIE_DOMAIN.lstrip(".")
        if parsed.scheme == "https" and (host == root or host.endswith("." + root)):
            return True
    if parsed.scheme in ("http", "https") and host in ("localhost", "127.0.0.1"):
        return True
    for prefix in allowed_extra:
        if redirect_uri.startswith(prefix):
            return True
    return False
