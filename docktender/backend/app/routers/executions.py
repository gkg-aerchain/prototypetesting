"""Execution & VO control: live dockings, the variation-order log priced against
the captured tariff, and approve/dispute actions."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.audit import audit
from ..db import get_db
from ..deps import get_current_user
from ..models import (
    Award,
    Bid,
    FinalAccount,
    Specification,
    Tender,
    User,
    VariationOrder,
    Vessel,
    Yard,
)
from ..schemas import VOIn, VOPatch

router = APIRouter(prefix="/api", tags=["executions"])
DEMO_TODAY = datetime(2026, 7, 3)


def _award_guard(db: Session, award_id: str, org_id: str) -> Award:
    aw = db.get(Award, award_id)
    if not aw:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Award not found")
    t = db.get(Tender, aw.tender_id)
    if not t or t.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Award not found")
    return aw


def _execution_summary(db: Session, aw: Award) -> dict:
    t = db.get(Tender, aw.tender_id)
    spec = db.get(Specification, t.spec_id) if t else None
    vessel = db.get(Vessel, spec.vessel_id) if spec else None
    bid = db.get(Bid, aw.bid_id)
    yard = db.get(Yard, bid.yard_id) if bid and bid.yard_id else None
    vos = list(db.scalars(select(VariationOrder).where(VariationOrder.award_id == aw.id)
                          .order_by(VariationOrder.vo_no)))
    approved = sum(v.proposed_usd for v in vos if v.state == "approved")
    open_count = sum(1 for v in vos if v.state in ("proposed", "disputed"))
    in_dock = False
    day = total = 0
    if bid and bid.slot_start and bid.slot_end:
        today = DEMO_TODAY
        if bid.slot_start <= today <= bid.slot_end:
            in_dock = True
            day = (today.date() - bid.slot_start.date()).days + 1
            total = (bid.slot_end.date() - bid.slot_start.date()).days + 1
    fa = db.scalar(select(FinalAccount).where(FinalAccount.award_id == aw.id))
    return {
        "award_id": aw.id, "tender_ref": t.ref if t else "", "vessel": vessel.name if vessel else "—",
        "yard": yard.name if yard else "—", "in_dock": in_dock, "dock_day": day, "dock_total": total,
        "vo_count": len(vos), "vo_open": open_count, "vo_approved_usd": round(approved, 2),
        "settled": fa is not None,
        "vos": [_vo_dict(v) for v in vos],
    }


def _vo_dict(v: VariationOrder) -> dict:
    over = None
    if v.tariff_usd is not None:
        over = round(v.proposed_usd - v.tariff_usd, 2)
    return {
        "id": v.id, "vo_no": v.vo_no, "title": v.title, "qty": v.qty, "uom": v.uom,
        "proposed_usd": v.proposed_usd, "tariff_line_ref": v.tariff_line_ref,
        "tariff_usd": v.tariff_usd, "over_tariff_usd": over, "state": v.state,
        "decided_by": v.decided_by,
    }


@router.get("/executions")
def list_executions(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    out = []
    for t in db.scalars(select(Tender).where(Tender.org_id == user.org_id, Tender.status == "awarded")):
        aw = db.scalar(select(Award).where(Award.tender_id == t.id))
        if aw:
            summary = _execution_summary(db, aw)
            if not summary["settled"]:  # settled dockings move to Settlements
                out.append(summary)
    return out


@router.get("/executions/{award_id}")
def get_execution(award_id: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> dict:
    return _execution_summary(db, _award_guard(db, award_id, user.org_id))


@router.post("/executions/{award_id}/vos", status_code=201)
def add_vo(award_id: str, body: VOIn, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)) -> dict:
    aw = _award_guard(db, award_id, user.org_id)
    n = db.scalar(select(func.count()).select_from(VariationOrder)
                  .where(VariationOrder.award_id == aw.id)) or 0
    vo = VariationOrder(
        org_id=user.org_id, award_id=aw.id, vo_no=f"VO-{n + 1:02d}", title=body.title,
        spec_item_id=body.spec_item_id, qty=body.qty, uom=body.uom,
        proposed_usd=body.proposed_usd, tariff_line_ref=body.tariff_line_ref,
        tariff_usd=body.tariff_usd, state="proposed",
    )
    db.add(vo)
    db.flush()
    audit(db, org_id=user.org_id, actor_id=user.id, action="vo_propose", entity="award", entity_id=aw.id)
    db.commit()
    return _vo_dict(vo)


@router.patch("/vos/{vo_id}")
def decide_vo(vo_id: str, body: VOPatch, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)) -> dict:
    vo = db.get(VariationOrder, vo_id)
    if not vo or vo.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "VO not found")
    if body.state not in ("approved", "disputed", "rejected"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid state")
    vo.state = body.state
    vo.decided_by = user.full_name or user.email
    vo.decided_at = datetime.now(timezone.utc)
    audit(db, org_id=user.org_id, actor_id=user.id, action=f"vo_{body.state}", entity="vo",
          entity_id=vo.id, detail={"reason": body.reason})
    db.commit()
    return _vo_dict(vo)
