"""Profile updates: theme + signal accent (the per-user setting) and name."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import MePatch, UserOut

router = APIRouter(prefix="/api", tags=["me"])

_ACCENTS = {"cerise", "marigold", "verdigris", "azure", "violet"}
_THEMES = {"system", "light", "dark"}


@router.patch("/me", response_model=UserOut)
def patch_me(
    body: MePatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if body.accent is not None:
        if body.accent not in _ACCENTS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown accent")
        user.accent = body.accent
    if body.theme is not None:
        if body.theme not in _THEMES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown theme")
        user.theme = body.theme
    if body.full_name is not None:
        user.full_name = body.full_name
    db.commit()
    db.refresh(user)
    return user
