"""Settlements: final-account reconciliation, fleet KPIs, and yard scorecards."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
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
    YardScore,
)
from ..schemas import SettlementIn

router = APIRouter(prefix="/api", tags=["settlements"])


@router.get("/settlements")
def list_settlements(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    accounts = []
    growths = []
    for t in db.scalars(select(Tender).where(Tender.org_id == user.org_id, Tender.status == "awarded")):
        aw = db.scalar(select(Award).where(Award.tender_id == t.id))
        if not aw:
            continue
        fa = db.scalar(select(FinalAccount).where(FinalAccount.award_id == aw.id))
        if not fa:
            continue
        spec = db.get(Specification, t.spec_id)
        vessel = db.get(Vessel, spec.vessel_id) if spec else None
        bid = db.get(Bid, aw.bid_id)
        yard = db.get(Yard, bid.yard_id) if bid and bid.yard_id else None
        growths.append(fa.growth_pct)
        accounts.append({
            "award_id": aw.id, "tender_ref": t.ref, "vessel": vessel.name if vessel else "—",
            "yard": yard.name if yard else "—", "quoted_usd": fa.quoted_usd,
            "final_usd": fa.final_usd, "growth_pct": fa.growth_pct,
            "lines": fa.lines_json, "closed_at": fa.closed_at.isoformat() if fa.closed_at else None,
        })
    # yard scorecards
    scorecards = []
    for y in db.scalars(select(Yard)):
        scores = list(db.scalars(select(YardScore).where(YardScore.yard_id == y.id)))
        if not scores:
            continue
        scorecards.append({
            "yard": y.name, "region": y.region, "dockings": len(scores),
            "avg_growth_pct": round(sum(s.growth_pct for s in scores) / len(scores), 1),
            "avg_overrun_days": round(sum(s.overrun_days for s in scores) / len(scores), 1),
            "quality": round(sum(s.quality for s in scores) / len(scores), 1),
            "hse": round(sum(s.hse for s in scores) / len(scores), 1),
        })
    scorecards.sort(key=lambda s: s["avg_growth_pct"])
    kpi = {
        "avg_growth_pct": round(sum(growths) / len(growths), 1) if growths else 0.0,
        "settled_count": len(accounts),
    }
    return {"accounts": accounts, "scorecards": scorecards, "kpi": kpi}


@router.post("/settlements/{award_id}/close")
def close_settlement(award_id: str, body: SettlementIn, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)) -> dict:
    aw = db.get(Award, award_id)
    if not aw:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Award not found")
    t = db.get(Tender, aw.tender_id)
    if not t or t.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Award not found")
    if db.scalar(select(FinalAccount).where(FinalAccount.award_id == aw.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Already settled")

    bid = db.get(Bid, aw.bid_id)
    # quoted = the awarded normalized bid; final = quoted + approved VOs (or override)
    from ..models import TecComponent, Evaluation

    quoted = 0.0
    ev = db.scalar(select(Evaluation).where(Evaluation.tender_id == t.id))
    if ev:
        c = db.scalar(select(TecComponent).where(TecComponent.evaluation_id == ev.id,
                                                 TecComponent.bid_id == aw.bid_id))
        quoted = c.normalized_usd if c else 0.0
    approved_vos = sum(v.proposed_usd for v in db.scalars(
        select(VariationOrder).where(VariationOrder.award_id == aw.id, VariationOrder.state == "approved")))
    final = body.final_usd or round(quoted + approved_vos, 2)
    growth = round((final / quoted - 1) * 100, 1) if quoted else 0.0
    fa = FinalAccount(
        award_id=aw.id, quoted_usd=quoted, final_usd=final, growth_pct=growth,
        lines_json=body.lines or [
            {"section": "Contract price", "quoted": quoted, "final": quoted},
            {"section": "Approved variations", "quoted": 0, "final": round(final - quoted, 2)},
        ],
        closed_at=datetime.now(timezone.utc),
    )
    db.add(fa)
    # record a yard scorecard entry
    if bid and bid.yard_id:
        db.add(YardScore(yard_id=bid.yard_id, docking_ref=t.ref, growth_pct=growth,
                         overrun_days=0, quality=4, hse=4))
    audit(db, org_id=user.org_id, actor_id=user.id, action="settle", entity="award", entity_id=aw.id)
    db.commit()
    return {"award_id": aw.id, "quoted_usd": quoted, "final_usd": final, "growth_pct": growth}
