"""Docking-superintendent assistant. Read-only, org-scoped tools; cites evidence
(norm basis, tender ref); never reveals a sealed bid before its deadline."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .client import get_client
from ..core.config import settings
from ..models import (
    Bid,
    Evaluation,
    Specification,
    TecComponent,
    Tender,
    User,
    Vessel,
    WorkItem,
    Yard,
)

SYSTEM = (
    "You are DockTender's assistant to a ship-management docking superintendent. Answer with "
    "the specific, correct terminology of ship-repair procurement (docking window, SS/IS, UWILD, "
    "TEC, VO, off-hire, mh/t, Sa 2.5, general services). Use the provided tools to ground every "
    "answer in this organisation's real data; cite the tender ref or the guide-norm basis you relied "
    "on. Explain the Total Evaluated Cost logic plainly: the lowest sticker is often not the lowest "
    "evaluated cost once deviation, off-hire and VO exposure are priced. Never disclose the contents "
    "of a sealed bid before its tender deadline. Be concise."
)

TOOLS = [
    {"name": "get_programme", "description": "Fleet docking programme: vessels, windows, tenders in flight.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_tender", "description": "A tender's leveling result by ref (e.g. TND-2026-014): TEC ranking + recommendation.",
     "input_schema": {"type": "object", "properties": {"ref": {"type": "string"}}, "required": ["ref"], "additionalProperties": False}},
    {"name": "get_vessel", "description": "A vessel's particulars and docking window by name.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"], "additionalProperties": False}},
    {"name": "get_norm", "description": "A work-item guide norm by code (e.g. ST-001) or keyword.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False}},
]


def chat(db: Session, user: User, messages: list[dict]) -> str | None:
    client = get_client()
    if client is None:
        return None
    convo = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] in ("user", "assistant")]

    for _ in range(6):  # bounded tool loop
        resp = client.messages.create(
            model=settings.anthropic_model, max_tokens=1500, system=SYSTEM,
            tools=TOOLS, messages=convo,
        )
        if resp.stop_reason == "tool_use":
            convo.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    out = _run_tool(db, user, block.name, block.input)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})
            convo.append({"role": "user", "content": results})
            continue
        return "".join(b.text for b in resp.content if b.type == "text")
    return "I wasn't able to complete that — please rephrase."


def _run_tool(db: Session, user: User, name: str, args: dict) -> str:
    import json

    if name == "get_programme":
        vessels = list(db.scalars(select(Vessel).where(Vessel.org_id == user.org_id)))
        tenders = list(db.scalars(select(Tender).where(Tender.org_id == user.org_id)))
        return json.dumps({
            "vessels": [{"name": v.name, "type": v.vessel_type, "last_docked": str(v.last_docking_date)} for v in vessels],
            "tenders": [{"ref": t.ref, "status": t.status} for t in tenders],
        })
    if name == "get_vessel":
        v = db.scalar(select(Vessel).where(Vessel.org_id == user.org_id,
                                           Vessel.name.ilike(f"%{args['name']}%")))
        if not v:
            return "No such vessel."
        from ..engines.clock import docking_window
        w = docking_window(last_docking_date=v.last_docking_date, special_survey_no=v.special_survey_no,
                           uwild_ok=v.uwild_ok, edd_enrolled=v.edd_enrolled)
        return json.dumps({"name": v.name, "type": v.vessel_type, "dwt": v.dwt,
                           "window": w.to_dict()})
    if name == "get_tender":
        t = db.scalar(select(Tender).where(Tender.org_id == user.org_id, Tender.ref == args["ref"]))
        if not t:
            return "No such tender."
        # respect sealed bids before deadline
        now = datetime.now(timezone.utc)
        if t.sealed and t.deadline and t.deadline.replace(tzinfo=timezone.utc) > now:
            return json.dumps({"ref": t.ref, "status": t.status, "note": "Bids are sealed until the deadline; detail withheld."})
        ev = db.scalar(select(Evaluation).where(Evaluation.tender_id == t.id))
        if not ev:
            return json.dumps({"ref": t.ref, "status": t.status, "note": "No evaluation yet."})
        rows = []
        for c in db.scalars(select(TecComponent).where(TecComponent.evaluation_id == ev.id).order_by(TecComponent.rank)):
            bid = db.get(Bid, c.bid_id)
            yard = db.get(Yard, bid.yard_id) if bid and bid.yard_id else None
            tec = c.normalized_usd + c.deviation_usd + c.offhire_usd + c.vo_exposure_usd
            rows.append({"rank": c.rank, "yard": yard.name if yard else "—",
                         "tec_usd": round(tec), "sticker_usd": round(c.normalized_usd),
                         "recommended": c.recommended})
        return json.dumps({"ref": t.ref, "ranking": rows})
    if name == "get_norm":
        q = args["query"].lower()
        wi = db.scalar(select(WorkItem).where(WorkItem.code.ilike(f"%{q}%")))
        if not wi:
            wi = db.scalar(select(WorkItem).where(WorkItem.title.ilike(f"%{q}%")))
        if not wi:
            return "No matching work item."
        return json.dumps({"code": wi.code, "title": wi.title, "norm": wi.norm_value,
                           "unit": wi.norm_unit, "basis": wi.norm_basis})
    return "Unknown tool."
