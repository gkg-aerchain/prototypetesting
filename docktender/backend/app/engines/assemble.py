"""Assemble TEC engine inputs from stored bid data.

This is the single source of truth for turning a tender's persisted bids + bid
lines into `BidEval` objects. Both the demo seed and the live `POST /evaluate`
endpoint call it, so the demo's headline numbers are produced by exactly the same
path a real, user-created tender uses — there is no separate hardcoded shortcut.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Bid, SpecItem, Tender, Yard
from .normalization import level_bid
from .tec import BidEval


def _yard_name(db: Session, yard_id: str | None) -> str:
    if not yard_id:
        return "—"
    y = db.get(Yard, yard_id)
    return y.name if y else "—"


def _is_crit(bid: Bid, n_exclusions: int, has_below_norm: bool) -> bool:
    """A bid carries a critical exposure flag when it exposes the owner to the
    classic final-account blow-up: a below-norm man-hour rate on a to-be-confirmed
    quantity, or a bid with no tariff annexed and multiple scope exclusions. The
    recommendation engine skips the lowest-TEC bid when it is crit-flagged."""
    if has_below_norm:
        return True
    if not bid.tariff_captured and n_exclusions >= 3:
        return True
    return False


def build_bid_evals(db: Session, tender: Tender) -> list[BidEval]:
    """Read the tender's stored bids and produce engine inputs.

    N (normalized) is computed by `level_bid` over the bid's reviewed/portal priced
    lines with the tender's frozen FX. D/O/V inputs (deviation distance, port fees,
    exclusion medians, below-norm extras, growth factor) are read from the fields
    captured on the Bid and its lines — never invented here.
    """
    spec_items = list(db.scalars(select(SpecItem).where(SpecItem.spec_id == tender.spec_id)))
    bids = list(db.scalars(select(Bid).where(Bid.tender_id == tender.id)))
    fx = tender.fx_rates_json or {}

    evals: list[BidEval] = []
    for bid in bids:
        leveled = level_bid(bid, spec_items, fx)

        excluded_items: list[dict] = []
        below_norm_items: list[dict] = []
        n_exclusions = 0
        for line in bid.lines:
            if line.state in ("excluded", "unpriced") and line.exposure_median_usd:
                excluded_items.append({
                    "label": line.raw_text or "Excluded item",
                    "median_usd": float(line.exposure_median_usd),
                })
                n_exclusions += 1
            elif line.state == "excluded":
                n_exclusions += 1
            if line.below_norm_usd:
                below_norm_items.append({
                    "label": line.raw_text or "Below-norm item",
                    "extra_usd": float(line.below_norm_usd),
                })

        evals.append(BidEval(
            bid_id=bid.id,
            yard_name=_yard_name(db, bid.yard_id),
            normalized_usd=leveled.normalized_usd,
            dock_days=bid.dock_days,
            deviation_nm=bid.deviation_nm,
            deviation_port_fees=bid.port_fees_usd,
            excluded_items=excluded_items,
            below_norm_items=below_norm_items,
            growth_pct=bid.growth_pct,
            has_crit_flag=_is_crit(bid, n_exclusions, bool(below_norm_items)),
            sticker_usd=leveled.normalized_usd,
        ))
    return evals
