"""Public profile lookup for other apps (friends, etc.)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import CurrentUserId
from app.db import get_db
from app.models import User
from app.schemas.auth import UserPublicOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserPublicOut])
def list_users_by_ids(
    ids: str = Query(..., description="Comma-separated user ids"),
    user_id: CurrentUserId = None,
    db: Session = Depends(get_db),
):
    """Return basic profiles for the given ids. Requires authentication."""
    _ = user_id  # auth gate
    try:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ids must be comma-separated integers",
        ) from e
    if not id_list:
        return []
    if len(id_list) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At most 100 ids per request",
        )
    rows = db.query(User).filter(User.id.in_(id_list)).all()
    by_id = {u.id: u for u in rows}
    return [
        UserPublicOut(
            id=i,
            name=by_id[i].name if i in by_id else None,
            avatar_url=by_id[i].avatar_url if i in by_id else None,
        )
        for i in id_list
        if i in by_id
    ]


@router.get("/by-email", response_model=UserPublicOut)
def get_user_by_email(
    email: str = Query(..., min_length=3),
    user_id: CurrentUserId = None,
    db: Session = Depends(get_db),
):
    """Resolve a user id by email (for friend invites across apps)."""
    _ = user_id
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user:
        # Case-insensitive fallback
        user = db.query(User).filter(User.email.ilike(email.strip())).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserPublicOut(id=user.id, name=user.name, avatar_url=user.avatar_url)


@router.get("/{lookup_id}", response_model=UserPublicOut)
def get_user(
    lookup_id: int,
    user_id: CurrentUserId = None,
    db: Session = Depends(get_db),
):
    _ = user_id
    user = db.query(User).filter(User.id == lookup_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserPublicOut(id=user.id, name=user.name, avatar_url=user.avatar_url)
