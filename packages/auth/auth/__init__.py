"""Validate Accounts JWTs in FastAPI apps via JWKS."""

from auth.fastapi_deps import (
    AuthUser,
    CurrentUser,
    CurrentUserId,
    get_current_user,
    get_current_user_id,
    require_admin,
)

__all__ = [
    "AuthUser",
    "CurrentUser",
    "CurrentUserId",
    "get_current_user",
    "get_current_user_id",
    "require_admin",
]
