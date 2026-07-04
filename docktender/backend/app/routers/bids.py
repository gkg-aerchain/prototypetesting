"""Bid intake (portal + AI ingestion) and the human review screen.

The review screen is the product: AI-parsed lines land as drafts with per-line
confidence and never count toward leveling until a reviewer accepts them (stamps
reviewed_by). Portal bids are trusted as entered."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai import bid_parser
from ..ai.client import ai_available
from ..ai.sanity import run_sanity_check
from ..core.audit import audit
from ..db import get_db
from ..deps import get_current_user
from ..models import (
    AgentEvent,
    Bid,
    BidLine,
    Invitation,
    Specification,
    SpecItem,
    Tender,
    User,
    WorkItem,
    Yard,
)
from ..schemas import BidIn, BidLinePatch

router = APIRouter(prefix="/api", tags=["bids"])


def _tender(db: Session, tender_id: str, org_id: str) -> Tender:
    t = db.get(Tender, tender_id)
    if not t or t.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tender not found")
    return t


def _bid_guard(db: Session, bid_id: str, org_id: str) -> Bid:
    bid = db.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bid not found")
    t = db.get(Tender, bid.tender_id)
    if not t or t.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bid not found")
    return bid


@router.post("/tenders/{tender_id}/bids", status_code=201)
def create_portal_bid(tender_id: str, body: BidIn, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)) -> dict:
    """Structured portal bid — trusted as entered (no AI confidence)."""
    t = _tender(db, tender_id, user.org_id)
    yard = db.get(Yard, body.yard_id)
    if not yard:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Yard not found")
    bid = Bid(
        tender_id=t.id, yard_id=body.yard_id, currency=body.currency,
        dock_id=body.dock_id, dock_days=body.dock_days,
        tariff_captured=body.tariff_captured, source="portal",
        sealed_until=t.deadline, deviation_nm=body.deviation_nm,
        port_fees_usd=body.port_fees_usd, growth_pct=body.growth_pct,
    )
    db.add(bid)
    db.flush()
    for ln in body.lines:
        db.add(BidLine(
            bid_id=bid.id, spec_item_id=ln.spec_item_id, raw_text=ln.raw_text,
            uom=ln.uom, qty=ln.qty, rate=ln.rate, amount=ln.amount,
            state=ln.state, assumptions=ln.assumptions,
            exposure_median_usd=ln.exposure_median_usd, below_norm_usd=ln.below_norm_usd,
        ))
    _mark_invited(db, t, body.yard_id)
    audit(db, org_id=user.org_id, actor_id=user.id, action="bid_received", entity="tender", entity_id=t.id)
    db.commit()
    return {"bid_id": bid.id, "lines": len(body.lines)}


@router.post("/tenders/{tender_id}/bids/ingest", status_code=201)
def ingest_bid(tender_id: str, yard_id: str = Body(...), text: str = Body(...),
               user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Parse a pasted quotation into a draft bid with AI-mapped lines for review."""
    if not ai_available():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "AI ingestion unavailable — no API key configured. Enter the bid via the portal form.")
    t = _tender(db, tender_id, user.org_id)
    yard = db.get(Yard, yard_id)
    if not yard:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Yard not found")

    parsed = bid_parser.parse_quote(text)
    if parsed is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI ingestion unavailable")

    bid = Bid(
        tender_id=t.id, yard_id=yard_id, currency=parsed["currency"],
        dock_days=parsed["dock_days"], source="ai_ingest", sealed_until=t.deadline,
    )
    db.add(bid)
    db.flush()

    spec_items = list(db.scalars(select(SpecItem).where(SpecItem.spec_id == t.spec_id)))
    section_index = _section_index(db, t.spec_id, spec_items)
    low = 0
    for ln in parsed["lines"]:
        proposed = _propose_spec_item(ln.get("section_hint", ""), section_index)
        conf = ln.get("ai_confidence", 0.5)
        if conf < bid_parser.CONFIDENCE_THRESHOLD:
            low += 1
        db.add(BidLine(
            bid_id=bid.id, spec_item_id=None,  # proposed only; not attached until reviewed
            raw_text=ln.get("raw_text", ""), uom=ln.get("uom", ""),
            qty=ln.get("qty") or None, rate=ln.get("rate") or None,
            amount=ln.get("amount") or None, state=ln.get("state", "priced"),
            assumptions=f"proposed:{proposed}" if proposed else "",
            ai_confidence=conf,
        ))

    _mark_invited(db, t, yard_id)
    n_excl = sum(1 for ln in parsed["lines"] if ln.get("state") == "excluded")
    db.add(AgentEvent(
        org_id=user.org_id, agent="bid_parser", severity="info",
        vessel_id=_vessel_of(db, t),
        message=f"{yard.name} quotation ingested — {len(parsed['lines'])} lines mapped, {n_excl} exclusions detected.",
        evidence=f"{len(parsed['lines']) - low}/{len(parsed['lines'])} high confidence",
        needs_decision=low > 0,
    ))
    audit(db, org_id=user.org_id, actor_id=user.id, action="ingest_bid", entity="tender",
          entity_id=t.id, detail={"lines": len(parsed["lines"]), "low_confidence": low})
    db.commit()
    return {"bid_id": bid.id, "lines": len(parsed["lines"]), "low_confidence": low}


@router.get("/tenders/{tender_id}/bids")
def list_bids(tender_id: str, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)) -> list[dict]:
    """Bids received for a tender, with review progress for the review screen."""
    t = _tender(db, tender_id, user.org_id)
    out = []
    for bid in db.scalars(select(Bid).where(Bid.tender_id == t.id)):
        yard = db.get(Yard, bid.yard_id) if bid.yard_id else None
        lines = list(bid.lines)
        needs_review = [l for l in lines if l.ai_confidence is not None and l.reviewed_by is None]
        out.append({
            "bid_id": bid.id, "yard": yard.name if yard else "—",
            "region": yard.region if yard else "", "source": bid.source,
            "currency": bid.currency, "dock_days": bid.dock_days,
            "lines": len(lines), "unreviewed": len(needs_review),
            "tariff_captured": bid.tariff_captured,
        })
    return out


@router.get("/bids/{bid_id}/review")
def review_bid(bid_id: str, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> dict:
    bid = _bid_guard(db, bid_id, user.org_id)
    yard = db.get(Yard, bid.yard_id) if bid.yard_id else None
    t = db.get(Tender, bid.tender_id)
    spec_items = {si.id: si for si in db.scalars(select(SpecItem).where(SpecItem.spec_id == t.spec_id))}
    lines = []
    for ln in bid.lines:
        proposed = None
        if (ln.assumptions or "").startswith("proposed:"):
            proposed = ln.assumptions.split("proposed:", 1)[1]
        target = ln.spec_item_id or proposed
        target_title = spec_items[target].title if target in spec_items else None
        lines.append({
            "id": ln.id, "raw_text": ln.raw_text, "uom": ln.uom, "qty": ln.qty,
            "rate": ln.rate, "amount": ln.amount, "state": ln.state,
            "ai_confidence": ln.ai_confidence, "reviewed": ln.reviewed_by is not None,
            "spec_item_id": ln.spec_item_id, "proposed_spec_item_id": proposed,
            "target_title": target_title,
        })
    return {
        "bid_id": bid.id, "yard": yard.name if yard else "—", "source": bid.source,
        "currency": bid.currency, "dock_days": bid.dock_days,
        "spec_items": [{"id": si.id, "title": si.title, "line_no": si.line_no}
                       for si in sorted(spec_items.values(), key=lambda s: s.line_no)],
        "lines": lines,
    }


@router.patch("/bids/{bid_id}/lines/{line_id}")
def patch_line(bid_id: str, line_id: str, body: BidLinePatch,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    bid = _bid_guard(db, bid_id, user.org_id)
    line = db.get(BidLine, line_id)
    if not line or line.bid_id != bid.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Line not found")
    if body.spec_item_id is not None:
        line.spec_item_id = body.spec_item_id or None
    if body.state is not None:
        line.state = body.state
    if body.amount is not None:
        line.amount = body.amount
    if body.accept:
        # Accept the proposed mapping if none set explicitly.
        if line.spec_item_id is None and (line.assumptions or "").startswith("proposed:"):
            line.spec_item_id = line.assumptions.split("proposed:", 1)[1]
        line.reviewed_by = user.full_name or user.email
        line.reviewed_at = datetime.now(timezone.utc)
        line.assumptions = ""  # clear the proposed marker
    db.commit()
    return {"id": line.id, "reviewed": line.reviewed_by is not None,
            "spec_item_id": line.spec_item_id, "state": line.state}


@router.post("/bids/{bid_id}/sanity-check")
def sanity_check(bid_id: str, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> dict:
    """Run the guide-norm Sanity Checker over the bid's reviewed lines."""
    bid = _bid_guard(db, bid_id, user.org_id)
    t = db.get(Tender, bid.tender_id)
    events = run_sanity_check(db, bid, user.org_id, _vessel_of(db, t))
    db.commit()
    return {"findings": [{"severity": e.severity, "message": e.message, "evidence": e.evidence}
                         for e in events]}


# --------------------------------------------------------------------------- helpers
def _mark_invited(db: Session, t: Tender, yard_id: str) -> None:
    inv = db.scalar(select(Invitation).where(Invitation.tender_id == t.id, Invitation.yard_id == yard_id))
    if inv:
        inv.status = "bid_received"
    else:
        db.add(Invitation(tender_id=t.id, yard_id=yard_id, status="bid_received"))


def _vessel_of(db: Session, t: Tender) -> str | None:
    spec = db.get(Specification, t.spec_id)
    return spec.vessel_id if spec else None


def _section_index(db: Session, spec_id: str, spec_items: list[SpecItem]) -> dict[str, str]:
    """Map a section name (lowercased) to a representative spec_item id."""
    wi_section = {wi.id: wi.section_name for wi in db.scalars(select(WorkItem))}
    out: dict[str, str] = {}
    for si in spec_items:
        name = wi_section.get(si.work_item_id)
        if name and name.lower() not in out:
            out[name.lower()] = si.id
    return out


def _propose_spec_item(section_hint: str, section_index: dict[str, str]) -> str | None:
    if not section_hint:
        return None
    hint = section_hint.lower()
    for name, sid in section_index.items():
        if hint in name or name in hint:
            return sid
    # token overlap fallback
    hint_tokens = set(hint.split())
    for name, sid in section_index.items():
        if hint_tokens & set(name.split()):
            return sid
    return None
