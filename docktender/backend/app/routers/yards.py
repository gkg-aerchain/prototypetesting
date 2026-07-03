"""Yard directory + physical-fit filter. A dock fits a vessel when its length,
beam and depth-over-blocks clear the vessel with working margins."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Dock, User, Vessel, Yard, YardScore

router = APIRouter(prefix="/api", tags=["yards"])

# Working margins for a dock to accept a vessel.
LOA_MARGIN_M = 6.0
BEAM_MARGIN_M = 2.0
DRAFT_MARGIN_M = 0.5
# Vessels dock in light/ballast condition; docking draft is well below summer draft.
DOCKING_DRAFT_FACTOR = 0.6


def _dock_out(d: Dock, vessel: Vessel | None = None) -> dict:
    out = {
        "id": d.id, "name": d.name, "kind": d.kind, "length_m": d.length_m,
        "beam_m": d.beam_m, "depth_over_blocks_m": d.depth_over_blocks_m,
        "max_dwt": d.max_dwt, "cranes": d.cranes_json,
    }
    if vessel:
        fits, margins = _fit(d, vessel)
        out["fits"] = fits
        out["margins"] = margins
    return out


def _fit(d: Dock, v: Vessel):
    docking_draft = round(v.summer_draft_m * DOCKING_DRAFT_FACTOR, 1)
    l_margin = round(d.length_m - v.loa_m, 1)
    b_margin = round(d.beam_m - v.beam_m, 1)
    dep_margin = round(d.depth_over_blocks_m - docking_draft, 1)
    fits = (l_margin >= LOA_MARGIN_M and b_margin >= BEAM_MARGIN_M
            and dep_margin >= DRAFT_MARGIN_M and (d.max_dwt == 0 or d.max_dwt >= v.dwt))
    return fits, {"loa_m": l_margin, "beam_m": b_margin, "depth_m": dep_margin,
                  "docking_draft_m": docking_draft}


def _yard_out(db: Session, y: Yard, vessel: Vessel | None = None, with_docks=True) -> dict:
    out = {
        "id": y.id, "name": y.name, "country": y.country, "region": y.region,
        "labor_rate_band": y.labor_rate_band, "lat": y.lat, "lon": y.lon, "notes": y.notes,
    }
    if with_docks:
        docks = list(db.scalars(select(Dock).where(Dock.yard_id == y.id)))
        out["docks"] = [_dock_out(d, vessel) for d in docks]
        if vessel:
            out["fits"] = any(d.get("fits") for d in out["docks"])
    return out


@router.get("/yards")
def list_yards(region: str | None = None, vessel_id: str | None = None,
               fits_only: bool = False, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> list[dict]:
    vessel = None
    if vessel_id:
        vessel = db.get(Vessel, vessel_id)
        if not vessel or vessel.org_id != user.org_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vessel not found")
    stmt = select(Yard).order_by(Yard.name)
    if region:
        stmt = stmt.where(Yard.region == region)
    yards = [_yard_out(db, y, vessel) for y in db.scalars(stmt)]
    if vessel and fits_only:
        yards = [y for y in yards if y.get("fits")]
    return yards


@router.get("/yards/{yard_id}")
def get_yard(yard_id: str, vessel_id: str | None = None,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    y = db.get(Yard, yard_id)
    if not y:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Yard not found")
    vessel = db.get(Vessel, vessel_id) if vessel_id else None
    out = _yard_out(db, y, vessel)
    out["scores"] = [
        {"docking_ref": s.docking_ref, "growth_pct": s.growth_pct,
         "overrun_days": s.overrun_days, "quality": s.quality, "hse": s.hse, "notes": s.notes}
        for s in db.scalars(select(YardScore).where(YardScore.yard_id == y.id))
    ]
    return out
