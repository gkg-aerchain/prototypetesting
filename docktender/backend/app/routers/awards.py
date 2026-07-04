"""Award: create the award from the recommended (or chosen) bid, capture the
yard's tariff to the vault, and generate the award-memo PDF."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.audit import audit
from ..db import get_db
from ..deps import get_current_user
from ..engines.awards import build_award_memo
from ..models import (
    Award,
    Bid,
    Dock,
    Evaluation,
    Specification,
    Tariff,
    TecComponent,
    Tender,
    User,
    Vessel,
    Yard,
)
from ..schemas import AwardIn

router = APIRouter(prefix="/api", tags=["awards"])


def _tender(db: Session, tender_id: str, org_id: str) -> Tender:
    t = db.get(Tender, tender_id)
    if not t or t.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tender not found")
    return t


def _ranking(db: Session, tender: Tender) -> tuple[list[dict], dict | None]:
    ev = db.scalar(select(Evaluation).where(Evaluation.tender_id == tender.id)
                   .order_by(Evaluation.computed_at.desc()))
    if not ev:
        return [], None
    rows = []
    rec = None
    for c in db.scalars(select(TecComponent).where(TecComponent.evaluation_id == ev.id)
                        .order_by(TecComponent.rank)):
        bid = db.get(Bid, c.bid_id)
        yard = db.get(Yard, bid.yard_id) if bid and bid.yard_id else None
        tec = c.normalized_usd + c.deviation_usd + c.offhire_usd + c.vo_exposure_usd
        row = {"bid_id": c.bid_id, "rank": c.rank, "yard": yard.name if yard else "—",
               "tec_usd": tec, "recommended": c.recommended}
        rows.append(row)
        if c.recommended:
            rec = row
    return rows, rec


@router.post("/tenders/{tender_id}/award", status_code=201)
def award(tender_id: str, body: AwardIn, user: User = Depends(get_current_user),
          db: Session = Depends(get_db)) -> dict:
    t = _tender(db, tender_id, user.org_id)
    bid = db.get(Bid, body.bid_id)
    if not bid or bid.tender_id != t.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bid not found on this tender")
    if db.scalar(select(Award).where(Award.tender_id == t.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Tender already awarded")

    aw = Award(tender_id=t.id, bid_id=bid.id, memo_note=body.memo_note,
               checklist_json=body.checklist, awarded_at=datetime.now(timezone.utc))
    db.add(aw)
    t.status = "awarded"
    # Capture the awarded yard's tariff to the vault (if the bid brought one) — store
    # the bid's priced lines as the rate card that variation orders are priced against.
    if bid.tariff_captured:
        tariff_lines = [
            {"ref": ln.spec_item_id or ln.id, "item": ln.raw_text,
             "uom": ln.uom, "qty": ln.qty, "rate": ln.rate, "amount": ln.amount}
            for ln in bid.lines if ln.state == "priced" and ln.amount is not None
        ]
        db.add(Tariff(yard_id=bid.yard_id, bid_id=bid.id,
                      doc_name=f"{t.ref} standard tariff",
                      lines_json=tariff_lines or [{"note": "no priced lines captured"}]))
    audit(db, org_id=user.org_id, actor_id=user.id, action="award", entity="tender",
          entity_id=t.id, detail={"bid_id": bid.id})
    db.commit()
    return {"award_id": aw.id, "tender_status": t.status}


@router.get("/tenders/{tender_id}/award/preview")
def award_preview(tender_id: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> dict:
    """The award memo preview — ranking + auto-drafted rationale + checklist state."""
    t = _tender(db, tender_id, user.org_id)
    ranking, rec = _ranking(db, t)
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No evaluation to award from")
    rationale = _rationale(db, t, ranking, rec)
    spec = db.get(Specification, t.spec_id)
    vessel = db.get(Vessel, spec.vessel_id) if spec else None
    rec_bid = db.get(Bid, rec["bid_id"])
    return {
        "tender_ref": t.ref, "vessel": vessel.name if vessel else "—",
        "recommended_bid_id": rec["bid_id"], "recommended_yard": rec["yard"],
        "recommended_tec_usd": rec["tec_usd"], "ranking": ranking, "rationale": rationale,
        "checklist": {
            "tariff_annexed": bool(rec_bid and rec_bid.tariff_captured),
            "validity": bool(rec_bid and rec_bid.validity_date),
            "dock_confirmed": bool(rec_bid and rec_bid.dock_id),
            "terms": False,
        },
        "already_awarded": db.scalar(select(Award).where(Award.tender_id == t.id)) is not None,
    }


def _rationale(db: Session, tender: Tender, ranking: list[dict], rec: dict) -> str:
    if not ranking:
        return ""
    lowest_sticker = min(ranking, key=lambda r: _sticker(db, r["bid_id"]))
    ls = _sticker(db, lowest_sticker["bid_id"])
    if lowest_sticker["bid_id"] != rec["bid_id"]:
        return (f"The lowest sticker (${ls / 1e6:.2f}M, {lowest_sticker['yard']}) ranks below "
                f"{rec['yard']} once deviation, off-hire and VO exposure are priced — the cheapest "
                f"bid carries the highest total evaluated cost. {rec['yard']} offers the lowest TEC "
                f"with fully-confirmed scope.")
    return f"{rec['yard']} offers both the lowest sticker and the lowest total evaluated cost."


def _sticker(db: Session, bid_id: str) -> float:
    ev = db.scalar(select(Evaluation).order_by(Evaluation.computed_at.desc()))
    c = db.scalar(select(TecComponent).where(TecComponent.bid_id == bid_id,
                                             TecComponent.evaluation_id == ev.id)) if ev else None
    return c.normalized_usd if c else 0.0


@router.get("/awards/{award_id}/memo.pdf")
def award_memo_pdf(award_id: str, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> Response:
    aw = db.get(Award, award_id)
    if not aw:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Award not found")
    t = _tender(db, aw.tender_id, user.org_id)
    ranking, rec = _ranking(db, t)
    spec = db.get(Specification, t.spec_id)
    vessel = db.get(Vessel, spec.vessel_id) if spec else None
    awarded = next((r for r in ranking if r["bid_id"] == aw.bid_id), rec or {})
    pdf = build_award_memo(
        tender_ref=t.ref, vessel=vessel.name if vessel else "—",
        yard=awarded.get("yard", "—"), tec_usd=awarded.get("tec_usd", 0.0),
        ranking=ranking, rationale=_rationale(db, t, ranking, awarded) if ranking else "",
        checklist=aw.checklist_json or {}, memo_note=aw.memo_note or "",
    )
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="award-{t.ref}.pdf"'})
