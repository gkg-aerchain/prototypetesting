"""Sanity Checker — runs the guide-norm engine over a bid's reviewed lines and
emits agent events. This 'agent' is the norms table, not an LLM call; it is labelled
honestly as such. Findings carry the norm basis so they are checkable claims."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..engines.norms import check_rate
from ..models import AgentEvent, Bid, BidLine, SpecItem, WorkItem


def run_sanity_check(db: Session, bid: Bid, org_id: str, vessel_id: str | None) -> list[AgentEvent]:
    """Check each priced/reviewed line's implied rate against its work item's norm."""
    events: list[AgentEvent] = []
    for line in bid.lines:
        if line.spec_item_id is None or line.amount is None or not line.qty:
            continue
        si = db.get(SpecItem, line.spec_item_id)
        if not si or not si.work_item_id:
            continue
        wi = db.get(WorkItem, si.work_item_id)
        if not wi:
            continue
        implied_rate = line.amount / line.qty if line.qty else None
        flag = check_rate(bid_rate=implied_rate, work_item=wi, qty_tbc=si.qty_tbc)
        if flag:
            ev = AgentEvent(
                org_id=org_id, agent="sanity_checker", severity=flag.severity,
                vessel_id=vessel_id, message=f"{wi.title}: {flag.text}",
                evidence=flag.detail, needs_decision=(flag.severity == "crit"),
            )
            db.add(ev)
            events.append(ev)
    return events
