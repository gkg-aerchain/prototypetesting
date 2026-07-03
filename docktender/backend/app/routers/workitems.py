"""Canonical work-item library — read-only search for the spec builder."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User, WorkItem

router = APIRouter(prefix="/api", tags=["work-items"])


def _out(wi: WorkItem) -> dict:
    return {
        "id": wi.id, "code": wi.code, "section": wi.section, "section_name": wi.section_name,
        "title": wi.title, "uom": wi.uom, "norm_value": wi.norm_value,
        "norm_unit": wi.norm_unit, "norm_basis": wi.norm_basis, "factors": wi.factors_json,
        "typical": wi.typical,
    }


@router.get("/work-items")
def list_work_items(section: int | None = None, q: str | None = None,
                    user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(WorkItem)
    if section is not None:
        stmt = stmt.where(WorkItem.section == section)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(WorkItem.title).like(like),
                              func.lower(WorkItem.code).like(like)))
    stmt = stmt.order_by(WorkItem.section, WorkItem.code)
    return [_out(wi) for wi in db.scalars(stmt)]


@router.get("/work-items/sections")
def sections(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(WorkItem).order_by(WorkItem.section, WorkItem.code))
    counts: dict[int, dict] = {}
    for wi in rows:
        c = counts.setdefault(wi.section, {"section": wi.section, "name": wi.section_name, "count": 0})
        c["count"] += 1
    return list(counts.values())
