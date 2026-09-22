"""Identity user model (shared across all Nellits apps)."""
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=True)
    email = Column(String(256), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=True)
    password_reset_token_hash = Column(String(128), nullable=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)
    # Public URL path served from StaticFiles, e.g. /uploads/avatars/12_abc.jpg
    avatar_url = Column(String(512), nullable=True)
    # UI theme preference: "light" or "dark"
    theme = Column(String(8), nullable=True)
    is_admin = Column(Boolean, nullable=False, default=False, server_default="false")
