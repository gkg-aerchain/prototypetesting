"""Tender room: list/read tenders, invitations, clarifications/addenda."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.audit import audit
from ..db import get_db
from ..deps import get_current_user
from ..models import (
    Bid,
    Clarification,
    Invitation,
    Specification,
    Tender,
    User,
    Vessel,
    Yard,
)
from ..schemas import ClarificationAnswerIn, ClarificationIn, InviteIn, TenderIn

router = APIRouter(prefix="/api", tags=["tenders"])


def _tender_guard(db: Session, tender_id: str, org_id: str) -> Tender:
    t = db.get(Tender, tender_id)
    if not t or t.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tender not found")
    return t


def _tender_summary(db: Session, t: Tender) -> dict:
    spec = db.get(Specification, t.spec_id)
    vessel = db.get(Vessel, spec.vessel_id) if spec else None
    n_bids = db.scalar(select(func.count()).select_from(Bid).where(Bid.tender_id == t.id)) or 0
    n_inv = db.scalar(select(func.count()).select_from(Invitation).where(Invitation.tender_id == t.id)) or 0
    return {
        "id": t.id, "ref": t.ref, "status": t.status,
        "vessel": vessel.name if vessel else "—",
        "vessel_type": vessel.vessel_type if vessel else "",
        "spec_id": t.spec_id, "spec_title": spec.title if spec else "",
        "deadline": t.deadline.isoformat() if t.deadline else None,
        "offhire_usd_day": t.offhire_usd_day,
        "bids": n_bids, "invited": n_inv,
    }


@router.get("/tenders")
def list_tenders(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    tenders = db.scalars(select(Tender).where(Tender.org_id == user.org_id).order_by(Tender.ref.desc()))
    return [_tender_summary(db, t) for t in tenders]


@router.post("/tenders", status_code=201)
def create_tender(body: TenderIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> dict:
    spec = db.get(Specification, body.spec_id)
    if not spec or spec.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Specification not found")
    if spec.status != "frozen":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Freeze the specification before tendering")
    ref = _next_ref(db, user.org_id)
    t = Tender(
        org_id=user.org_id, spec_id=spec.id, ref=ref, status="draft",
        deadline=body.deadline, fx_date=body.fx_date, fx_rates_json=body.fx_rates,
        offhire_usd_day=body.offhire_usd_day, sealed=True,
    )
    db.add(t)
    db.flush()
    audit(db, org_id=user.org_id, actor_id=user.id, action="create", entity="tender", entity_id=t.id)
    db.commit()
    return _tender_summary(db, t)


def _next_ref(db: Session, org_id: str) -> str:
    year = datetime.now(timezone.utc).year
    n = (db.scalar(select(func.count()).select_from(Tender).where(Tender.org_id == org_id)) or 0) + 1
    return f"TND-{year}-{n:03d}"


@router.get("/tenders/{tender_id}")
def get_tender(tender_id: str, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> dict:
    t = _tender_guard(db, tender_id, user.org_id)
    out = _tender_summary(db, t)
    # invitations with yard + fit + bid status
    invites = []
    now = datetime.now(timezone.utc)
    deadline_passed = t.deadline is None or (t.deadline.replace(tzinfo=timezone.utc) <= now)
    for inv in db.scalars(select(Invitation).where(Invitation.tender_id == t.id)):
        yard = db.get(Yard, inv.yard_id) if inv.yard_id else None
        bid = db.scalar(select(Bid).where(Bid.tender_id == t.id, Bid.yard_id == inv.yard_id))
        invites.append({
            "yard_id": inv.yard_id, "yard": yard.name if yard else "—",
            "region": yard.region if yard else "", "status": inv.status,
            "has_bid": bid is not None,
        })
    out["invitations"] = invites
    out["sealed_bids_hidden"] = t.sealed and not deadline_passed
    out["clarifications"] = [
        {"id": c.id, "question": c.question, "answer": c.answer,
         "addendum_no": c.addendum_no, "published": c.published}
        for c in db.scalars(select(Clarification).where(Clarification.tender_id == t.id))
    ]
    return out


@router.post("/tenders/{tender_id}/issue")
def issue_tender(tender_id: str, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> dict:
    t = _tender_guard(db, tender_id, user.org_id)
    if not db.scalar(select(Invitation).where(Invitation.tender_id == t.id)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invite at least one yard first")
    t.status = "issued"
    audit(db, org_id=user.org_id, actor_id=user.id, action="issue", entity="tender", entity_id=t.id)
    db.commit()
    return _tender_summary(db, t)


@router.post("/tenders/{tender_id}/invite")
def invite(tender_id: str, body: InviteIn, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)) -> dict:
    t = _tender_guard(db, tender_id, user.org_id)
    added = 0
    for yid in body.yard_ids:
        if not db.get(Yard, yid):
            continue
        exists = db.scalar(select(Invitation).where(Invitation.tender_id == t.id, Invitation.yard_id == yid))
        if not exists:
            db.add(Invitation(tender_id=t.id, yard_id=yid, status="invited"))
            added += 1
    audit(db, org_id=user.org_id, actor_id=user.id, action="invite", entity="tender",
          entity_id=t.id, detail={"added": added})
    db.commit()
    return _tender_summary(db, t)


@router.post("/tenders/{tender_id}/clarifications", status_code=201)
def add_clarification(tender_id: str, body: ClarificationIn, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)) -> dict:
    t = _tender_guard(db, tender_id, user.org_id)
    c = Clarification(tender_id=t.id, question=body.question, asked_by=user.full_name)
    db.add(c)
    db.flush()
    audit(db, org_id=user.org_id, actor_id=user.id, action="clarification", entity="tender", entity_id=t.id)
    db.commit()
    return {"id": c.id, "question": c.question, "answer": c.answer,
            "addendum_no": c.addendum_no, "published": c.published}


@router.patch("/clarifications/{clar_id}")
def answer_clarification(clar_id: str, body: ClarificationAnswerIn,
                         user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    c = db.get(Clarification, clar_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    t = _tender_guard(db, c.tender_id, user.org_id)
    c.answer = body.answer
    if body.publish:
        c.published = True
        n = (db.scalar(select(func.count()).select_from(Clarification)
                       .where(Clarification.tender_id == t.id, Clarification.published == True)) or 0)  # noqa: E712
        c.addendum_no = n
    audit(db, org_id=user.org_id, actor_id=user.id, action="answer_clarification", entity="tender", entity_id=t.id)
    db.commit()
    return {"id": c.id, "question": c.question, "answer": c.answer,
            "addendum_no": c.addendum_no, "published": c.published}
