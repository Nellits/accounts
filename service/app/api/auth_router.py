"""Auth API: register, login, logout, me, password reset, token exchange."""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import (
    ACCESS_TOKEN_EXPIRE_DAYS,
    COOKIE_NAME,
    CurrentUserId,
    cookie_kwargs,
    create_access_token,
    hash_password,
    redirect_uri_allowed,
    verify_password,
)
from app.avatar_storage import (
    delete_stored_avatar,
    is_stored_avatar_file_missing,
    save_avatar_file,
)
from app.db import get_db
from app.models import User
from app.schemas.auth import (
    ChangePasswordIn,
    ForgotPasswordIn,
    LoginIn,
    MessageOut,
    RegisterIn,
    ResetPasswordIn,
    TokenIn,
    TokenOut,
    UserOut,
    UserPreferencesUpdate,
)
from app.services.password_reset_email import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _theme_out(raw: str | None) -> str | None:
    if raw in ("light", "dark"):
        return raw
    return None


def _reconcile_stale_avatar(user: User, db: Session) -> None:
    if user.avatar_url and is_stored_avatar_file_missing(user.avatar_url):
        user.avatar_url = None
        db.commit()
        db.refresh(user)


def _user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        has_password=bool(user.password_hash),
        avatar_url=user.avatar_url,
        theme=_theme_out(user.theme),
        is_admin=bool(user.is_admin),
    )


def _set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        value=token,
        **cookie_kwargs(max_age=ACCESS_TOKEN_EXPIRE_DAYS * 24 * 3600),
    )


def _issue_token(user: User) -> str:
    return create_access_token(user.id, email=user.email, is_admin=bool(user.is_admin))


@router.post("/register", response_model=UserOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )
    user = User(
        email=email,
        name=body.name or email.split("@")[0],
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = _issue_token(user)
    resp = JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=_user_to_out(user).model_dump(),
    )
    _set_session_cookie(resp, token)
    return resp


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    _reconcile_stale_avatar(user, db)
    resp = JSONResponse(content=_user_to_out(user).model_dump())
    _set_session_cookie(resp, _issue_token(user))
    return resp


@router.post("/token", response_model=TokenOut)
def token(body: TokenIn, db: Session = Depends(get_db)):
    """Email + password -> JWT (Bearer). For mobile / native clients."""
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    _reconcile_stale_avatar(user, db)
    access = _issue_token(user)
    return TokenOut(
        access_token=access,
        expires_in=ACCESS_TOKEN_EXPIRE_DAYS * 24 * 3600,
        user=_user_to_out(user),
    )


@router.get("/login")
def login_page_redirect(
    redirect_uri: str | None = Query(None),
):
    """Browser entry: serve SPA login (frontend handles ?redirect_uri=)."""
    # Static SPA is mounted at /; this keeps a stable API-ish path if needed.
    q = urlencode({"redirect_uri": redirect_uri}) if redirect_uri else ""
    return RedirectResponse(url=f"/login{('?' + q) if q else ''}", status_code=302)


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _expires_aware(expires_at: datetime | None) -> datetime | None:
    if expires_at is None:
        return None
    if expires_at.tzinfo is None:
        return expires_at.replace(tzinfo=timezone.utc)
    return expires_at


_RESET_LINK_INVALID = "Invalid or expired reset link. Please request a new one."
_FORGOT_PASSWORD_MESSAGE = (
    "If an account exists for this email, password reset instructions have been sent."
)


def _user_for_reset_token(raw_token: str, db: Session) -> User | None:
    token = raw_token.strip()
    if not token:
        return None
    token_hash = _hash_reset_token(token)
    user = db.query(User).filter(User.password_reset_token_hash == token_hash).first()
    expires = _expires_aware(user.password_reset_expires_at) if user else None
    if not user or expires is None or expires < datetime.now(timezone.utc):
        return None
    return user


@router.post("/forgot-password", response_model=MessageOut)
def forgot_password(body: ForgotPasswordIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    out = MessageOut(message=_FORGOT_PASSWORD_MESSAGE)
    if not user or not user.password_hash or not user.email:
        return out

    raw_token = secrets.token_urlsafe(32)
    user.password_reset_token_hash = _hash_reset_token(raw_token)
    user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()

    frontend = os.getenv("PASSWORD_RESET_FRONTEND_URL", "http://localhost:5175").rstrip("/")
    reset_url = f"{frontend}/reset-password?{urlencode({'token': raw_token})}"
    try:
        send_password_reset_email(user.email, reset_url)
    except Exception:
        logger.exception("Failed to send password reset email to %s", user.email)
    return out


@router.get("/reset-password/validate")
def validate_reset_token(token: str | None = Query(None), db: Session = Depends(get_db)):
    user = _user_for_reset_token(token or "", db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_RESET_LINK_INVALID)
    return {"ok": True}


@router.post("/reset-password", response_model=MessageOut)
def reset_password(body: ResetPasswordIn, db: Session = Depends(get_db)):
    user = _user_for_reset_token(body.token, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_RESET_LINK_INVALID)
    user.password_hash = hash_password(body.password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    db.commit()
    return MessageOut(message="Your password has been updated. You can sign in now.")


@router.post("/change-password", response_model=UserOut)
def change_password(
    body: ChangePasswordIn,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has no password on file.",
        )
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if verify_password(body.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password",
        )
    user.password_hash = hash_password(body.new_password)
    db.commit()
    db.refresh(user)
    _reconcile_stale_avatar(user, db)
    resp = JSONResponse(content=_user_to_out(user).model_dump())
    _set_session_cookie(resp, _issue_token(user))
    return resp


@router.post("/logout")
def logout():
    resp = JSONResponse(content={"ok": True})
    kwargs = cookie_kwargs()
    resp.delete_cookie(
        key=COOKIE_NAME,
        path=kwargs.get("path", "/"),
        domain=kwargs.get("domain"),
    )
    return resp


@router.get("/me", response_model=UserOut)
def me(user_id: CurrentUserId, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _reconcile_stale_avatar(user, db)
    return _user_to_out(user)


@router.patch("/me", response_model=UserOut)
def update_me(
    body: UserPreferencesUpdate,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.name is not None:
        user.name = body.name
    if body.theme is not None:
        user.theme = body.theme
    db.commit()
    db.refresh(user)
    _reconcile_stale_avatar(user, db)
    return _user_to_out(user)


@router.post("/me/avatar", response_model=UserOut)
async def upload_my_avatar(
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    ct = (file.content_type or "").split(";")[0].strip().lower()
    data = await file.read()
    try:
        public_path = save_avatar_file(user_id, data, ct)
    except ValueError as e:
        code = str(e)
        if code == "unsupported_image_type":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use a JPEG, PNG, or WebP image",
            ) from e
        if code == "file_too_large":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image must be 2MB or smaller",
            ) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image") from e

    previous = user.avatar_url
    user.avatar_url = public_path
    db.commit()
    db.refresh(user)
    delete_stored_avatar(previous)
    return _user_to_out(user)


@router.delete("/me/avatar", response_model=UserOut)
def delete_my_avatar(user_id: CurrentUserId, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    previous = user.avatar_url
    user.avatar_url = None
    db.commit()
    db.refresh(user)
    delete_stored_avatar(previous)
    return _user_to_out(user)


@router.get("/complete-login")
def complete_login(
    redirect_uri: str = Query(...),
    user_id: CurrentUserId = None,
):
    """After SPA login, redirect browser to allowlisted app URL (cookie already set)."""
    _ = user_id
    if not redirect_uri_allowed(redirect_uri):
        raise HTTPException(status_code=400, detail="redirect_uri not allowed")
    return RedirectResponse(url=redirect_uri, status_code=302)
