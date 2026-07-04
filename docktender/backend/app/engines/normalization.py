"""Bid normalization: frozen-FX conversion, unit conversion, and leveling a bid's
lines onto the canonical spec grid. The human review screen is the product; this
engine only accelerates it — unreviewed AI-proposed lines do not count toward a
bid's normalized total."""
from __future__ import annotations

from dataclasses import dataclass, field

# Unit conversion factors to a canonical base per dimension.
_AREA = {"m2": 1.0, "ft2": 0.09290304}
_MASS = {"t": 1.0, "kg": 0.001, "tonne": 1.0}
_LENGTH = {"m": 1.0, "ft": 0.3048}


class UnknownUnitError(ValueError):
    pass


def to_base(amount: float, ccy: str, fx_rates: dict[str, float]) -> float:
    """Convert an amount in `ccy` to USD using the tender's frozen FX table.
    fx_rates maps CCY -> USD per 1 unit of CCY. USD passes through."""
    if ccy.upper() == "USD":
        return amount
    rate = fx_rates.get(ccy.upper())
    if rate is None:
        raise UnknownUnitError(f"No frozen FX rate for {ccy}")
    return amount * rate


def unit_convert(qty: float, from_uom: str, to_uom: str) -> float:
    """Convert a quantity between compatible units. Raises on unknown/incompatible
    pairs so the review UI can surface it rather than guessing silently."""
    f, t = from_uom.lower(), to_uom.lower()
    if f == t:
        return qty
    for table in (_AREA, _MASS, _LENGTH):
        if f in table and t in table:
            return qty * table[f] / table[t]
    raise UnknownUnitError(f"Cannot convert {from_uom} -> {to_uom}")


@dataclass
class LeveledLine:
    spec_item_id: str
    matched: bool
    state: str  # priced|included|excluded|unpriced
    normalized_usd: float
    raw_texts: list[str] = field(default_factory=list)


@dataclass
class LeveledBid:
    bid_id: str
    normalized_usd: float
    by_spec_item: dict[str, LeveledLine]
    exclusions: list[str]  # spec_item_ids excluded or unpriced
    unmatched_lines: list[str]  # bid line ids that mapped to no spec item


def _line_counts(line) -> bool:
    """A bid line contributes to the normalized total only if it is a real priced
    line and — when it came from AI ingestion — has been reviewed by a human."""
    if line.state != "priced" or line.amount is None:
        return False
    if line.ai_confidence is not None and line.reviewed_by is None:
        return False
    return True


def level_bid(bid, spec_items, fx_rates: dict[str, float]) -> LeveledBid:
    """Aggregate a bid's lines onto the spec grid.

    bid: object with .id, .currency, .lines (each line has spec_item_id, state,
         amount, ai_confidence, reviewed_by, raw_text)
    spec_items: iterable of spec item objects with .id
    """
    by_item: dict[str, LeveledLine] = {
        si.id: LeveledLine(si.id, matched=False, state="unpriced", normalized_usd=0.0)
        for si in spec_items
    }
    unmatched: list[str] = []
    total = 0.0

    for line in bid.lines:
        sid = line.spec_item_id
        if sid is None or sid not in by_item:
            # A line not yet mapped to a spec item is surfaced for review, but if it is
            # a real counted priced line it is still money in the bid and contributes to
            # the normalized total (dropping it would understate N and desync leveling).
            if sid is None:
                unmatched.append(line.id)
            if _line_counts(line):
                total += to_base(line.amount, bid.currency, fx_rates)
            continue
        ll = by_item[sid]
        ll.matched = True
        ll.raw_texts.append(line.raw_text or "")
        # State precedence: a priced+counted line makes the item priced.
        if _line_counts(line):
            usd = to_base(line.amount, bid.currency, fx_rates)
            ll.normalized_usd += usd
            ll.state = "priced"
            total += usd
        elif line.state in ("excluded", "unpriced") and ll.state not in ("priced",):
            ll.state = line.state
        elif line.state == "included" and ll.state not in ("priced",):
            ll.state = "included"

    exclusions = [sid for sid, ll in by_item.items() if ll.state in ("excluded", "unpriced")]
    return LeveledBid(
        bid_id=bid.id,
        normalized_usd=round(total, 2),
        by_spec_item=by_item,
        exclusions=exclusions,
        unmatched_lines=unmatched,
    )
