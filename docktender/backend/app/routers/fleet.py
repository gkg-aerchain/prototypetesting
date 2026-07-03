"""Fleet registry: vessels CRUD + the docking-window computed view."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.audit import audit
from ..db import get_db
from ..deps import get_current_user
from ..engines.clock import docking_window
from ..models import User, Vessel
from ..schemas import VesselIn

router = APIRouter(prefix="/api", tags=["fleet"])


def _today_for(user: User, db: Session) -> date:
    from .programme import programme_today
    from ..models import Organization

    org = db.get(Organization, user.org_id)
    return programme_today(org.name if org else "")


def _vessel_out(v: Vessel, today: date) -> dict:
    w = docking_window(
        last_docking_date=v.last_docking_date, special_survey_no=v.special_survey_no,
        uwild_ok=v.uwild_ok, edd_enrolled=v.edd_enrolled, today=today,
    )
    return {
        "id": v.id, "name": v.name, "vessel_type": v.vessel_type, "dwt": v.dwt,
        "loa_m": v.loa_m, "beam_m": v.beam_m, "summer_draft_m": v.summer_draft_m,
        "gt": v.gt, "built_year": v.built_year, "class_society": v.class_society,
        "last_docking_date": v.last_docking_date.isoformat() if v.last_docking_date else None,
        "last_docking_yard": v.last_docking_yard, "special_survey_no": v.special_survey_no,
        "uwild_ok": v.uwild_ok, "edd_enrolled": v.edd_enrolled, "tce_usd_day": v.tce_usd_day,
        "notes": v.notes, "window": w.to_dict(),
    }


@router.get("/fleet")
def list_fleet(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    today = _today_for(user, db)
    vessels = db.scalars(select(Vessel).where(Vessel.org_id == user.org_id).order_by(Vessel.name))
    return [_vessel_out(v, today) for v in vessels]


@router.get("/vessels/{vessel_id}")
def get_vessel(vessel_id: str, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> dict:
    v = db.get(Vessel, vessel_id)
    if not v or v.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vessel not found")
    return _vessel_out(v, _today_for(user, db))


@router.post("/vessels", status_code=201)
def create_vessel(body: VesselIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> dict:
    v = Vessel(org_id=user.org_id, **body.model_dump())
    db.add(v)
    db.flush()
    audit(db, org_id=user.org_id, actor_id=user.id, action="create", entity="vessel", entity_id=v.id)
    db.commit()
    return _vessel_out(v, _today_for(user, db))


@router.patch("/vessels/{vessel_id}")
def update_vessel(vessel_id: str, body: VesselIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> dict:
    v = db.get(Vessel, vessel_id)
    if not v or v.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vessel not found")
    for k, val in body.model_dump().items():
        setattr(v, k, val)
    audit(db, org_id=user.org_id, actor_id=user.id, action="update", entity="vessel", entity_id=v.id)
    db.commit()
    return _vessel_out(v, _today_for(user, db))


@router.delete("/vessels/{vessel_id}", status_code=204)
def delete_vessel(vessel_id: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> None:
    v = db.get(Vessel, vessel_id)
    if not v or v.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vessel not found")
    db.delete(v)
    audit(db, org_id=user.org_id, actor_id=user.id, action="delete", entity="vessel", entity_id=vessel_id)
    db.commit()
