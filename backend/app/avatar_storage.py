"""Store user profile avatars on disk."""
import os
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
UPLOADS_ROOT = Path(os.environ.get("ACCOUNTS_UPLOADS_DIR", str(BACKEND_ROOT / "uploads"))).resolve()
AVATARS_DIR = UPLOADS_ROOT / "avatars"

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_AVATAR_BYTES = 2 * 1024 * 1024


def ensure_avatar_dir() -> None:
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)


def is_stored_avatar_file_missing(avatar_url: str | None) -> bool:
    if not avatar_url or not avatar_url.startswith("/uploads/avatars/"):
        return False
    name = Path(avatar_url).name
    if ".." in name or "/" in name or "\\" in name:
        return True
    path = (AVATARS_DIR / name).resolve()
    if path.parent != AVATARS_DIR.resolve():
        return True
    return not path.is_file()


def delete_stored_avatar(avatar_url: str | None) -> None:
    if not avatar_url or not avatar_url.startswith("/uploads/avatars/"):
        return
    name = Path(avatar_url).name
    if ".." in name or "/" in name or "\\" in name:
        return
    path = (AVATARS_DIR / name).resolve()
    if path.parent != AVATARS_DIR.resolve():
        return
    if path.is_file():
        path.unlink()


def save_avatar_file(user_id: int, data: bytes, content_type: str) -> str:
    ext = ALLOWED_CONTENT_TYPES.get(content_type.split(";")[0].strip().lower())
    if not ext:
        raise ValueError("unsupported_image_type")
    if len(data) > MAX_AVATAR_BYTES:
        raise ValueError("file_too_large")
    ensure_avatar_dir()
    token = uuid.uuid4().hex[:16]
    filename = f"{user_id}_{token}{ext}"
    path = AVATARS_DIR / filename
    path.write_bytes(data)
    return f"/uploads/avatars/{filename}"
