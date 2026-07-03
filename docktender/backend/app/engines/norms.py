"""Guide-norm deviation checks — the "Sanity Checker" reads a bid line against the
canonical work item's guide norm and flags rates that fall outside a credible band.
Every flag carries the norm_basis so the finding is a checkable claim, not marketing.
"""
from __future__ import annotations

from dataclasses import dataclass

LOW_FACTOR = 0.60   # below 0.60x the norm low band -> under-priced warning
HIGH_FACTOR = 1.80  # above 1.80x the norm -> over-priced warning


@dataclass
class NormFlag:
    severity: str  # info|warn|crit
    text: str      # e.g. "104 mh/t - 48% vs norm"
    detail: str    # e.g. "Norm 230 mh/t - guide: Butler T3.1"


def _low_band(work_item) -> float:
    factors = work_item.factors_json or {}
    band = factors.get("band")
    if isinstance(band, list) and band:
        return float(band[0])
    return float(work_item.norm_value)


def check_rate(
    *,
    bid_rate: float | None,
    work_item,
    qty_tbc: bool = False,
) -> NormFlag | None:
    """Compare a bid's per-unit rate/man-hours to the work item's guide norm.

    bid_rate is in the work item's norm_unit (e.g. mh/t). Returns a flag or None.
    """
    if bid_rate is None or work_item is None or not work_item.norm_value:
        return None
    norm = float(work_item.norm_value)
    low_band = _low_band(work_item)
    basis = f"Norm {_fmt(norm)} {work_item.norm_unit} - {work_item.norm_basis}"

    if bid_rate < LOW_FACTOR * low_band:
        pct = round((1 - bid_rate / low_band) * 100)
        severity = "crit" if qty_tbc else "warn"
        suffix = " on a to-be-confirmed quantity (final-account growth pattern)" if qty_tbc else ""
        return NormFlag(
            severity=severity,
            text=f"{_fmt(bid_rate)} {work_item.norm_unit} - {pct}% vs norm",
            detail=basis + suffix,
        )
    if bid_rate > HIGH_FACTOR * norm:
        pct = round((bid_rate / norm - 1) * 100)
        return NormFlag(
            severity="warn",
            text=f"{_fmt(bid_rate)} {work_item.norm_unit} - +{pct}% above norm band",
            detail=basis,
        )
    return None


def _fmt(v: float) -> str:
    return f"{v:.0f}" if float(v).is_integer() else f"{v:.1f}"
