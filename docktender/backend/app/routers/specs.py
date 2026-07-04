"""Specification builder: create specs, add/import/copy items, freeze/version."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.audit import audit
from ..db import get_db
from ..deps import get_current_user
from ..models import Specification, SpecItem, Tender, User, Vessel, WorkItem
from ..schemas import SpecIn, SpecItemIn, SpecItemPatch

router = APIRouter(prefix="/api", tags=["specs"])


def _guard(db: Session, spec_id: str, org_id: str) -> Specification:
    s = db.get(Specification, spec_id)
    if not s or s.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Specification not found")
    return s


def _spec_summary(db: Session, s: Specification) -> dict:
    vessel = db.get(Vessel, s.vessel_id)
    n_items = db.scalar(select(func.count()).select_from(SpecItem).where(SpecItem.spec_id == s.id)) or 0
    # section coverage: how many of the 10 sections have at least one line
    covered = _section_coverage(db, s)
    return {
        "id": s.id, "title": s.title, "status": s.status, "version": s.version,
        "vessel_id": s.vessel_id, "vessel": vessel.name if vessel else "—",
        "vessel_type": vessel.vessel_type if vessel else "",
        "items": n_items, "sections_covered": covered, "sections_total": 10,
        "pct_complete": round(covered / 10 * 100),
        "frozen_at": s.frozen_at.isoformat() if s.frozen_at else None,
        "window_start": s.docking_window_start.isoformat() if s.docking_window_start else None,
        "window_end": s.docking_window_end.isoformat() if s.docking_window_end else None,
    }


def _section_coverage(db: Session, s: Specification) -> int:
    wi_section = {wi.id: wi.section for wi in db.scalars(select(WorkItem))}
    secs = set()
    for si in db.scalars(select(SpecItem).where(SpecItem.spec_id == s.id)):
        if si.work_item_id in wi_section:
            secs.add(wi_section[si.work_item_id])
    return len(secs)


@router.get("/specs")
def list_specs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    specs = db.scalars(select(Specification).where(Specification.org_id == user.org_id)
                       .order_by(Specification.created_at.desc()))
    return [_spec_summary(db, s) for s in specs]


@router.post("/specs", status_code=201)
def create_spec(body: SpecIn, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)) -> dict:
    vessel = db.get(Vessel, body.vessel_id)
    if not vessel or vessel.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vessel not found")
    s = Specification(org_id=user.org_id, vessel_id=vessel.id, title=body.title, status="draft")
    db.add(s)
    db.flush()
    audit(db, org_id=user.org_id, actor_id=user.id, action="create", entity="spec", entity_id=s.id)
    db.commit()
    return _spec_summary(db, s)


@router.get("/specs/{spec_id}")
def get_spec(spec_id: str, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)) -> dict:
    s = _guard(db, spec_id, user.org_id)
    out = _spec_summary(db, s)
    wi_map = {wi.id: wi for wi in db.scalars(select(WorkItem))}
    items = []
    for si in db.scalars(select(SpecItem).where(SpecItem.spec_id == s.id).order_by(SpecItem.line_no)):
        wi = wi_map.get(si.work_item_id)
        items.append({
            "id": si.id, "line_no": si.line_no, "title": si.title, "qty": si.qty,
            "uom": si.uom, "qty_tbc": si.qty_tbc, "origin": si.origin, "notes": si.notes,
            "code": wi.code if wi else None, "section": wi.section if wi else None,
            "section_name": wi.section_name if wi else None,
            "norm_value": wi.norm_value if wi else None, "norm_unit": wi.norm_unit if wi else None,
            "norm_basis": wi.norm_basis if wi else None,
        })
    out["item_list"] = items
    return out


@router.post("/specs/{spec_id}/items", status_code=201)
def add_items(spec_id: str, body: list[SpecItemIn], user: User = Depends(get_current_user),
              db: Session = Depends(get_db)) -> dict:
    s = _guard(db, spec_id, user.org_id)
    if s.status == "frozen":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Specification is frozen")
    start = db.scalar(select(func.max(SpecItem.line_no)).where(SpecItem.spec_id == s.id)) or 0
    for i, item in enumerate(body, start=1):
        wi = db.get(WorkItem, item.work_item_id) if item.work_item_id else None
        db.add(SpecItem(
            spec_id=s.id, work_item_id=item.work_item_id, line_no=start + i,
            title=item.title or (wi.title if wi else ""), qty=item.qty,
            uom=item.uom or (wi.uom if wi else ""), qty_tbc=item.qty_tbc,
            origin=item.origin, notes=item.notes,
        ))
    audit(db, org_id=user.org_id, actor_id=user.id, action="add_items", entity="spec",
          entity_id=s.id, detail={"count": len(body)})
    db.commit()
    return _spec_summary(db, s)


@router.patch("/specs/{spec_id}/items/{item_id}")
def update_item(spec_id: str, item_id: str, body: SpecItemPatch,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Edit a spec line — quantity, unit, TBC flag, origin, notes. Blocked once the
    spec is frozen (a frozen spec is the contractual scope sent to yards)."""
    s = _guard(db, spec_id, user.org_id)
    if s.status == "frozen":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Specification is frozen")
    si = db.get(SpecItem, item_id)
    if not si or si.spec_id != s.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Line not found")
    for field in ("qty", "uom", "qty_tbc", "origin", "notes", "title"):
        val = getattr(body, field)
        if val is not None:
            setattr(si, field, val)
    audit(db, org_id=user.org_id, actor_id=user.id, action="update_item", entity="spec_item",
          entity_id=si.id)
    db.commit()
    return {"id": si.id, "line_no": si.line_no, "title": si.title, "qty": si.qty,
            "uom": si.uom, "qty_tbc": si.qty_tbc, "origin": si.origin, "notes": si.notes}


@router.delete("/specs/{spec_id}/items/{item_id}", status_code=204)
def delete_item(spec_id: str, item_id: str, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)) -> None:
    s = _guard(db, spec_id, user.org_id)
    if s.status == "frozen":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Specification is frozen")
    si = db.get(SpecItem, item_id)
    if si and si.spec_id == s.id:
        db.delete(si)
        db.commit()


@router.post("/specs/{spec_id}/copy-forward")
def copy_forward(spec_id: str, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> dict:
    """Copy items from the vessel's most recent frozen spec into this draft."""
    s = _guard(db, spec_id, user.org_id)
    if s.status == "frozen":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Specification is frozen")
    prev = db.scalar(
        select(Specification).where(
            Specification.vessel_id == s.vessel_id, Specification.id != s.id,
            Specification.status == "frozen"
        ).order_by(Specification.frozen_at.desc()))
    if not prev:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No previous frozen specification to copy")
    start = db.scalar(select(func.max(SpecItem.line_no)).where(SpecItem.spec_id == s.id)) or 0
    n = 0
    for si in db.scalars(select(SpecItem).where(SpecItem.spec_id == prev.id).order_by(SpecItem.line_no)):
        n += 1
        db.add(SpecItem(
            spec_id=s.id, work_item_id=si.work_item_id, line_no=start + n, title=si.title,
            qty=si.qty, uom=si.uom, qty_tbc=si.qty_tbc, origin="previous", notes=si.notes,
        ))
    audit(db, org_id=user.org_id, actor_id=user.id, action="copy_forward", entity="spec",
          entity_id=s.id, detail={"from": prev.id, "count": n})
    db.commit()
    return _spec_summary(db, s)


@router.post("/specs/{spec_id}/freeze")
def freeze_spec(spec_id: str, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)) -> dict:
    s = _guard(db, spec_id, user.org_id)
    n = db.scalar(select(func.count()).select_from(SpecItem).where(SpecItem.spec_id == s.id)) or 0
    if n == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Add at least one line before freezing")
    s.status = "frozen"
    s.frozen_at = datetime.now(timezone.utc)
    audit(db, org_id=user.org_id, actor_id=user.id, action="freeze", entity="spec", entity_id=s.id)
    db.commit()
    return _spec_summary(db, s)
