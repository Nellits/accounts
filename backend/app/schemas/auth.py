"""Auth request/response schemas."""
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenIn(BaseModel):
    """Mobile / API token exchange (email + password -> JWT)."""

    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserOut"


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    password: str = Field(min_length=6)


class MessageOut(BaseModel):
    message: str


class UserOut(BaseModel):
    id: int
    email: Optional[str]
    name: Optional[str]
    has_password: bool = True
    avatar_url: Optional[str] = None
    theme: Optional[Literal["dark", "light"]] = None
    is_admin: bool = False


class UserPublicOut(BaseModel):
    """Minimal profile for cross-app display (friends, etc.)."""

    id: int
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserPreferencesUpdate(BaseModel):
    name: Optional[str] = None
    theme: Optional[Literal["dark", "light"]] = None


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


TokenOut.model_rebuild()
