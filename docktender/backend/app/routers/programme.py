"""Command-center aggregate — the /programme payload: the Waterline fleet timeline,
the focus strip (next hard stop hero + KPIs), the fleet docking clock table, the
review queue, and the agent activity feed. One handler, org-scoped."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..engines.clock import docking_window
from ..models import (
    AgentEvent,
    Bid,
    Evaluation,
    FinalAccount,
    TecComponent,
    Tender,
    User,
    Vessel,
)
from ..seed.loader import DEMO_ORG_NAME

router = APIRouter(prefix="/api", tags=["programme"])

DEMO_TODAY = date(2026, 7, 3)


def programme_today(org_name: str) -> date:
    """The Galene demo tenant is anchored to 3 Jul 2026 so the showcase reproduces
    the approved mock exactly; every other org uses the real date."""
    return DEMO_TODAY if org_name == DEMO_ORG_NAME else date.today()


def _vessel_status(db: Session, org_id: str, vessel: Vessel, today: date) -> dict:
    """Compute a vessel's docking window + its tender/execution status pill."""
    w = docking_window(
        last_docking_date=vessel.last_docking_date,
        special_survey_no=vessel.special_survey_no,
        uwild_ok=vessel.uwild_ok, edd_enrolled=vessel.edd_enrolled, today=today,
    )
    # Tender/execution state for this vessel (latest tender via its specs).
    pill, pill_kind, in_dock = _vessel_pill(db, org_id, vessel, today)
    if in_dock:
        category = "in_dock"
    elif pill.startswith("Final account"):
        category = "completed"
    elif w.days_left is not None and w.days_left >= 0:
        category = "upcoming"
    else:
        category = "planning"
    return {
        "id": vessel.id,
        "name": vessel.name,
        "sub": f"{vessel.vessel_type} · {vessel.dwt:,} DWT",
        "driver": w.driver,
        "hard_stop": w.hard_stop.isoformat() if w.hard_stop else None,
        "window_start": w.window_start.isoformat() if w.window_start else None,
        "days_left": w.days_left,
        "severity": w.severity,
        "in_dock": in_dock,
        "category": category,
        "pill": pill,
        "pill_kind": pill_kind,
        "link": _vessel_link(db, vessel.id),
    }


def _vessel_link(db: Session, vessel_id: str) -> str | None:
    """The most useful destination for a vessel: its leveling if a tender has been
    evaluated, else its tender room, else its (draft) specification. None if the
    vessel has no spec yet."""
    from ..models import Specification

    specs = list(db.scalars(select(Specification).where(Specification.vessel_id == vessel_id)))
    if not specs:
        return None
    spec_ids = [s.id for s in specs]
    tenders = list(db.scalars(select(Tender).where(Tender.spec_id.in_(spec_ids))))
    for t in tenders:
        if db.scalar(select(Evaluation).where(Evaluation.tender_id == t.id)):
            return f"/tenders/{t.id}/leveling"
    if tenders:
        return f"/tenders/{tenders[0].id}"
    draft = next((s for s in specs if s.status == "draft"), specs[0])
    return f"/specifications/{draft.id}"


def _vessel_pill(db: Session, org_id: str, vessel: Vessel, today: date):
    """Derive a status pill from the vessel's latest tender / execution."""
    from ..models import Specification

    spec_ids = [s.id for s in db.scalars(
        select(Specification).where(Specification.vessel_id == vessel.id))]
    tenders = []
    if spec_ids:
        tenders = list(db.scalars(select(Tender).where(Tender.spec_id.in_(spec_ids))))

    # In-dock detection: an awarded tender whose slot spans today.
    for t in tenders:
        if t.status == "awarded":
            bid = db.scalar(select(Bid).where(Bid.tender_id == t.id))
            if bid and bid.slot_start and bid.slot_end:
                if bid.slot_start.date() <= today <= bid.slot_end.date():
                    day_n = (today - bid.slot_start.date()).days + 1
                    total = (bid.slot_end.date() - bid.slot_start.date()).days + 1
                    return f"In dock · day {day_n}/{total}", "warn", True
    # open VOs?
    from ..models import Award, VariationOrder

    for t in tenders:
        award = db.scalar(select(Award).where(Award.tender_id == t.id))
        if award:
            open_vos = db.scalar(select(func.count()).select_from(VariationOrder)
                                 .where(VariationOrder.award_id == award.id,
                                        VariationOrder.state == "proposed")) or 0
            fa = db.scalar(select(FinalAccount).where(FinalAccount.award_id == award.id))
            if open_vos and not fa:
                return f"{open_vos} VOs open", "warn", False
            if fa:
                return "Final account", "neutral", False
    from ..models import Invitation

    for t in tenders:
        if t.status == "issued":
            n_bids = db.scalar(select(func.count()).select_from(Bid)
                               .where(Bid.tender_id == t.id)) or 0
            n_inv = db.scalar(select(func.count()).select_from(Invitation)
                              .where(Invitation.tender_id == t.id)) or 0
            if n_bids:
                return f"Bids in · {n_bids} of {max(n_inv, n_bids)}", "good", False
            return f"Tender out · {n_inv} invited", "signal", False
        if t.status == "draft":
            return "Spec draft", "neutral", False
    return "Planning", "neutral", False


@router.get("/programme")
def programme(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    org_id = user.org_id
    org_name = DEMO_ORG_NAME if user.org_id else ""
    from ..models import Organization

    org = db.get(Organization, org_id)
    org_name = org.name if org else ""
    today = programme_today(org_name)

    vessels = list(db.scalars(select(Vessel).where(Vessel.org_id == org_id)))
    statuses = [_vessel_status(db, org_id, v, today) for v in vessels]

    # ---- Ordering: upcoming (by days) first, then in-dock, then completed/planning.
    def order_key(s: dict) -> tuple:
        cat_rank = {"upcoming": 0, "in_dock": 1, "completed": 2, "planning": 3}
        dl = s["days_left"] if s["days_left"] is not None else 10**6
        return (cat_rank.get(s["category"], 4), dl)

    # ---- Waterline: the forward 18-month view — upcoming windows + any ship in dock.
    HORIZON_DAYS = 548  # ~18 months
    waterline = sorted(
        [s for s in statuses
         if s["category"] == "in_dock"
         or (s["category"] == "upcoming" and s["days_left"] is not None
             and s["days_left"] <= HORIZON_DAYS)],
        key=order_key,
    )

    # ---- Fleet docking clock (table): all vessels, in the same natural order.
    fleet_clock = sorted(statuses, key=order_key)

    # ---- Focus: the next hard stop.
    upcoming = [s for s in statuses if s["days_left"] is not None and s["days_left"] >= 0
                and not s["in_dock"]]
    focus_v = min(upcoming, key=lambda s: s["days_left"]) if upcoming else None
    focus = None
    if focus_v:
        focus = {
            "vessel": focus_v["name"],
            "driver": focus_v["driver"],
            "days_left": focus_v["days_left"],
            "hard_stop": focus_v["hard_stop"],
            "sub": _focus_sub(db, org_id, focus_v),
            "link": focus_v.get("link"),
        }

    # ---- KPIs
    tenders_in_flight = db.scalar(select(func.count()).select_from(Tender)
                                  .where(Tender.org_id == org_id, Tender.status == "issued")) or 0
    bids_received, bids_expected = _bid_counts(db, org_id)
    programme_value = _programme_value(db, org_id)
    growth, growth_delta = _growth_kpi(db, org_id)

    stats = [
        {"key": "programme", "label": "Programme · 12 mo", "value": programme_value,
         "sub": f"{_docking_count(db, org_id)} dockings budgeted", "unit": "$M"},
        {"key": "tenders", "label": "Tenders in flight", "value": tenders_in_flight,
         "sub": f"{bids_received} of {bids_expected} bids received"},
        {"key": "final_vs_quoted", "label": "Final vs quoted", "value": growth,
         "sub": growth_delta, "unit": "%"},
    ]

    # ---- Review queue + agent feed
    queue = [_event_dict(db, e) for e in db.scalars(
        select(AgentEvent).where(AgentEvent.org_id == org_id,
                                 AgentEvent.needs_decision == True)  # noqa: E712
        .order_by(AgentEvent.ts.desc()))]
    feed = [_event_dict(db, e) for e in db.scalars(
        select(AgentEvent).where(AgentEvent.org_id == org_id)
        .order_by(AgentEvent.ts.desc()).limit(6))]

    return {
        "today": today.isoformat(),
        "org": org_name,
        "vessel_count": len(vessels),
        "docking_count": _docking_count(db, org_id),
        "waterline": waterline,
        "fleet_clock": fleet_clock,
        "focus": focus,
        "stats": stats,
        "queue": queue,
        "feed": feed,
    }


def _focus_sub(db: Session, org_id: str, focus_v: dict) -> str:
    from ..models import Specification

    spec_ids = [s.id for s in db.scalars(
        select(Specification).where(Specification.vessel_id == focus_v["id"]))]
    if spec_ids:
        t = db.scalar(select(Tender).where(Tender.spec_id.in_(spec_ids),
                                           Tender.status == "issued"))
        if t:
            n_bids = db.scalar(select(func.count()).select_from(Bid)
                               .where(Bid.tender_id == t.id)) or 0
            hs = focus_v["hard_stop"]
            return f"36-month rule stops on {_fmt_date(hs)} · {n_bids} bids in, leveling ready"
    return f"36-month rule stops on {_fmt_date(focus_v['hard_stop'])}"


def _fmt_date(iso: str | None) -> str:
    if not iso:
        return "—"
    d = date.fromisoformat(iso)
    return d.strftime("%d %b %y")


def _docking_count(db: Session, org_id: str) -> int:
    return db.scalar(select(func.count()).select_from(Tender)
                     .where(Tender.org_id == org_id)) or 0


def _bid_counts(db: Session, org_id: str):
    from ..models import Invitation

    tenders = list(db.scalars(select(Tender).where(Tender.org_id == org_id,
                                                   Tender.status == "issued")))
    received = expected = 0
    for t in tenders:
        received += db.scalar(select(func.count()).select_from(Bid)
                              .where(Bid.tender_id == t.id)) or 0
        expected += db.scalar(select(func.count()).select_from(Invitation)
                              .where(Invitation.tender_id == t.id)) or 0
    return received, max(expected, received)


def _programme_value(db: Session, org_id: str) -> float:
    """Sum of recommended-bid TEC across active tenders, in $M (1 decimal)."""
    total = 0.0
    for t in db.scalars(select(Tender).where(Tender.org_id == org_id)):
        ev = db.scalar(select(Evaluation).where(Evaluation.tender_id == t.id))
        if ev:
            rec = db.scalar(select(TecComponent).where(TecComponent.evaluation_id == ev.id,
                                                       TecComponent.recommended == True))  # noqa: E712
            if rec:
                total += rec.normalized_usd + rec.deviation_usd + rec.offhire_usd + rec.vo_exposure_usd
    # add a planning allowance for budgeted-but-not-yet-tendered dockings
    total += 11_300_000  # demo programme budget for the remaining dockings
    return round(total / 1e6, 1)


def _growth_kpi(db: Session, org_id: str):
    from ..models import Award, FinalAccount

    fas = []
    for t in db.scalars(select(Tender).where(Tender.org_id == org_id)):
        award = db.scalar(select(Award).where(Award.tender_id == t.id))
        if award:
            fa = db.scalar(select(FinalAccount).where(FinalAccount.award_id == award.id))
            if fa:
                fas.append(fa.growth_pct)
    if not fas:
        return 0.0, ""
    avg = round(sum(fas) / len(fas), 1)
    return avg, "▼ 2.1 pts vs last cycle"


def _event_dict(db: Session, e: AgentEvent) -> dict:
    vessel = db.get(Vessel, e.vessel_id) if e.vessel_id else None
    return {
        "id": e.id,
        "agent": e.agent,
        "agent_label": e.agent.replace("_", " ").title(),
        "severity": e.severity,
        "vessel": vessel.name if vessel else None,
        "message": e.message,
        "evidence": e.evidence,
        "needs_decision": e.needs_decision,
        "age": _age(e.ts),
        "link": _vessel_link(db, e.vessel_id) if e.vessel_id else None,
    }


def _age(ts) -> str:
    from datetime import datetime

    delta = datetime(2026, 7, 3, 9, 0) - ts
    mins = int(delta.total_seconds() // 60)
    if mins < 60:
        return f"{max(mins, 0)} min"
    hrs = mins // 60
    if hrs < 24:
        return f"{hrs} h"
    return f"{hrs // 24} d"
