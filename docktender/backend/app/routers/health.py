"""Liveness + seed status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db import get_db
from ..models import WorkItem, Yard

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    work_items = db.scalar(select(func.count()).select_from(WorkItem)) or 0
    yards = db.scalar(select(func.count()).select_from(Yard)) or 0
    return {
        "status": "ok",
        "version": settings.version,
        "seeded": work_items > 0 and yards > 0,
        "work_items": work_items,
        "yards": yards,
    }
