"""Leveling matrix + TEC ranking — the money screen. Assembles the TEC cards, the
by-section normalized matrix (best cell = lowest priced with scope confirmed), and
the itemized exposure model, all from the stored evaluation."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import (
    Bid,
    BidLine,
    Dock,
    Evaluation,
    SpecItem,
    TecComponent,
    Tender,
    User,
    WorkItem,
    Yard,
)
from ..schemas import EvaluateIn

router = APIRouter(prefix="/api", tags=["leveling"])

LEGEND = [
    {"key": "normalized", "label": "Normalized bid", "color": "s1"},
    {"key": "deviation", "label": "Deviation", "color": "s2"},
    {"key": "offhire", "label": "Off-hire", "color": "s3"},
    {"key": "vo_exposure", "label": "VO exposure", "color": "s4"},
]


def _guard(db: Session, tender_id: str, org_id: str) -> Tender:
    t = db.get(Tender, tender_id)
    if not t or t.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tender not found")
    return t


def _bid_flags(db: Session, bid: Bid, comp: TecComponent) -> list[dict]:
    flags = []
    flags.append({"kind": "ok" if bid.tariff_captured else "warn",
                  "text": "Tariff captured" if bid.tariff_captured else "No tariff annexed"})
    n_excl = sum(1 for l in bid.lines if l.state == "excluded")
    n_unpriced = [l for l in bid.lines if l.state == "unpriced"]
    if n_excl == 0 and not n_unpriced:
        flags.append({"kind": "ok", "text": "0 exclusions"})
    elif n_excl > 0:
        flags.append({"kind": "warn", "text": f"{n_excl} exclusion{'s' if n_excl != 1 else ''}"})
    for l in n_unpriced:
        flags.append({"kind": "warn", "text": f"{l.raw_text} unpriced"})
    for f in comp.flags_json or []:
        if f.get("kind") == "below_norm":
            flags.append({"kind": "warn", "text": "Steel −48% vs norm"})
    return flags


@router.get("/tenders/{tender_id}/leveling")
def leveling(tender_id: str, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)) -> dict:
    t = _guard(db, tender_id, user.org_id)
    n_bids = db.scalar(select(func.count()).select_from(Bid).where(Bid.tender_id == t.id)) or 0
    ev = db.scalar(select(Evaluation).where(Evaluation.tender_id == t.id)
                   .order_by(Evaluation.computed_at.desc()))
    if not ev:
        # Graceful empty state — a tender with no evaluation yet is a normal stage,
        # not an error. The screen shows an empty leveling with the bid count.
        return {
            "tender_ref": t.ref, "spec_line_count": 0,
            "fx_date": t.fx_date.isoformat() if t.fx_date else None,
            "offhire_usd_day": t.offhire_usd_day, "legend": LEGEND,
            "cards": [], "matrix": {"columns": [], "rows": []}, "exposure": [],
            "bids_received": n_bids, "evaluated": False,
        }

    comps = list(db.scalars(select(TecComponent).where(TecComponent.evaluation_id == ev.id)
                            .order_by(TecComponent.rank)))
    bids = {b.id: b for b in db.scalars(select(Bid).where(Bid.tender_id == t.id))}

    cards = []
    for c in comps:
        bid = bids.get(c.bid_id)
        if not bid:
            continue
        yard = db.get(Yard, bid.yard_id) if bid.yard_id else None
        dock = db.get(Dock, bid.dock_id) if bid.dock_id else None
        tec = c.normalized_usd + c.deviation_usd + c.offhire_usd + c.vo_exposure_usd
        cards.append({
            "bid_id": bid.id, "rank": c.rank, "recommended": c.recommended,
            "yard": yard.name if yard else "—",
            "dock": f"{dock.name} · {dock.length_m:.0f} m" if dock else "—",
            "slot": _slot(bid),
            "tec_usd": round(tec, 2),
            "sticker_usd": c.normalized_usd,
            "dock_days": bid.dock_days,
            "composition": [
                {"key": "normalized", "usd": c.normalized_usd, "color": "s1"},
                {"key": "deviation", "usd": c.deviation_usd, "color": "s2"},
                {"key": "offhire", "usd": c.offhire_usd, "color": "s3"},
                {"key": "vo_exposure", "usd": c.vo_exposure_usd, "color": "s4"},
            ],
            "deviation_nm": c.deviation_nm,
            "flags": _bid_flags(db, bid, c),
            "note": (bid.terms_json or {}).get("note", ""),
            "lowest_sticker": False,  # set below
        })
    # mark lowest sticker
    if cards:
        lo = min(cards, key=lambda k: k["sticker_usd"])
        lo["lowest_sticker"] = True

    matrix = _build_matrix(db, t, bids)
    exposure = _build_exposure(db, comps, bids)

    spec_lines = db.scalar(select(func.count()).select_from(SpecItem)
                           .where(SpecItem.spec_id == t.spec_id)) or 0
    return {
        "tender_ref": t.ref,
        "spec_line_count": spec_lines,
        "fx_date": t.fx_date.isoformat() if t.fx_date else None,
        "offhire_usd_day": t.offhire_usd_day,
        "legend": LEGEND,
        "cards": cards,
        "matrix": matrix,
        "exposure": exposure,
    }


def _slot(bid: Bid) -> str:
    if bid.slot_start and bid.slot_end:
        s = bid.slot_start.strftime("%d %b")
        e = bid.slot_end.strftime("%d %b")
        return f"slot {s}–{e}"
    return ""


def _build_matrix(db: Session, tender: Tender, bids: dict[str, Bid]) -> dict:
    """Rows = spec sections; columns = bids (in rank/order). Cell = normalized amount
    or excluded/unpriced. Best = lowest priced amount with no cell flag."""
    # section metadata via work items
    wi_section = {wi.id: (wi.section, wi.section_name) for wi in db.scalars(select(WorkItem))}
    si_section: dict[str, tuple[int, str]] = {}
    for si in db.scalars(select(SpecItem).where(SpecItem.spec_id == tender.spec_id)):
        if si.work_item_id in wi_section:
            si_section[si.id] = wi_section[si.work_item_id]

    ordered_bids = list(bids.values())
    columns = [{"bid_id": b.id, "yard": (db.get(Yard, b.yard_id).name if b.yard_id else "—")}
               for b in ordered_bids]

    # gather cells: section_name -> {bid_id: {amount, state, flag}}
    sections: dict[int, dict] = {}
    for b in ordered_bids:
        for line in b.lines:
            if line.spec_item_id is None or line.spec_item_id not in si_section:
                continue
            sec_no, sec_name = si_section[line.spec_item_id]
            row = sections.setdefault(sec_no, {"section": sec_no, "name": sec_name, "cells": {}})
            row["cells"][b.id] = {
                "amount": line.amount, "state": line.state,
                "flag": line.assumptions or None,
            }

    rows = []
    for sec_no in sorted(sections):
        row = sections[sec_no]
        # best = lowest priced amount with no flag
        candidates = [(bid_id, c["amount"]) for bid_id, c in row["cells"].items()
                      if c["state"] == "priced" and not c["flag"] and c["amount"] is not None]
        best_bid = min(candidates, key=lambda x: x[1])[0] if candidates else None
        cells = []
        for col in columns:
            c = row["cells"].get(col["bid_id"], {"amount": None, "state": "n/a", "flag": None})
            cells.append({
                "bid_id": col["bid_id"], "amount": c["amount"], "state": c["state"],
                "flag": c["flag"], "best": col["bid_id"] == best_bid,
            })
        rows.append({"section": sec_no, "name": row["name"], "cells": cells})

    return {"columns": columns, "rows": rows}


def _build_exposure(db: Session, comps: list[TecComponent], bids: dict[str, Bid]) -> list[dict]:
    """Itemized VO exposure per bid (the 'Open exposure model' drawer)."""
    out = []
    for c in comps:
        bid = bids.get(c.bid_id)
        yard = db.get(Yard, bid.yard_id) if bid and bid.yard_id else None
        out.append({
            "bid_id": c.bid_id, "yard": yard.name if yard else "—",
            "total_usd": c.vo_exposure_usd,
            "items": c.flags_json or [],
        })
    return out


@router.post("/tenders/{tender_id}/evaluate")
def evaluate_tender(tender_id: str, body: EvaluateIn, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)) -> dict:
    """Recompute the evaluation from the tender's bids and (optional) new params.
    Uses the normalization + TEC engines over the reviewed bid lines."""
    from ..core.audit import audit
    from ..engines.assemble import build_bid_evals
    from ..engines.tec import TecParams, evaluate as run_tec

    t = _guard(db, tender_id, user.org_id)
    evals = build_bid_evals(db, t)
    if not evals:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No bids to evaluate")

    params = TecParams(
        offhire_usd_day=body.offhire_usd_day or t.offhire_usd_day,
        growth_default=body.growth_default if body.growth_default is not None else 0.094,
        fuel_usd_t=body.fuel_usd_t or 580.0,
        speed_kn=body.speed_kn or 12.5,
    )
    comps = run_tec(evals, params)

    ev = Evaluation(tender_id=t.id, params_json={
        "offhire_usd_day": params.offhire_usd_day, "growth_default": params.growth_default,
        "fuel_usd_t": params.fuel_usd_t, "speed_kn": params.speed_kn,
    })
    db.add(ev)
    db.flush()
    for c in comps:
        db.add(TecComponent(
            evaluation_id=ev.id, bid_id=c.bid_id, normalized_usd=c.normalized_usd,
            deviation_usd=c.deviation_usd, offhire_usd=c.offhire_usd,
            vo_exposure_usd=c.vo_exposure_usd, deviation_nm=c.deviation_nm,
            deviation_days=c.deviation_days, rank=c.rank, recommended=c.recommended,
            flags_json=[{"label": i.label, "kind": i.kind, "exposure_usd": i.exposure_usd}
                        for i in c.exposure.items],
        ))
    audit(db, org_id=user.org_id, actor_id=user.id, action="evaluate", entity="tender", entity_id=t.id)
    db.commit()
    return leveling(tender_id, user, db)
