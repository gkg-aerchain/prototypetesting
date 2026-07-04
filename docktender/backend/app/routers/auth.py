"""Authentication + current-user profile."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.audit import audit
from ..core.security import create_access_token, hash_password, verify_password
from ..db import get_db
from ..deps import get_current_user
from ..models import Organization, User
from ..schemas import LoginIn, MePatch, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    existing = db.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    org = Organization(name=body.company or f"{body.full_name or body.email}'s org", kind="manager")
    db.add(org)
    db.flush()
    user = User(
        org_id=org.id,
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="admin",  # first user of a new org is its admin
    )
    db.add(user)
    db.flush()
    audit(db, org_id=org.id, actor_id=user.id, action="register", entity="user", entity_id=user.id)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    from sqlalchemy import func

    from ..models import Vessel

    org = db.get(Organization, user.org_id)
    vessel_count = db.scalar(select(func.count()).select_from(Vessel)
                             .where(Vessel.org_id == user.org_id)) or 0
    return UserOut(
        id=user.id, email=user.email, full_name=user.full_name, role=user.role,
        accent=user.accent, theme=user.theme, org_id=user.org_id,
        org=org.name if org else "", vessel_count=vessel_count,
    )
