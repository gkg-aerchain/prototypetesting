"""Total Evaluated Cost — the money engine.

    TEC = N + D + O + V
      N  normalized priced bid (frozen FX)                    <- normalization.py
      D  deviation: fuel of extra steaming + port/canal dues
      O  off-hire: dock days x vessel TCE
      V  VO exposure: excluded/unpriced work + growth          <- exposure.py

The recommendation is the lowest TEC with no critical flag; if the lowest carries a
crit flag, the next clean bid is recommended and an explanation flag is attached — the
design shows one clear answer, it never argues both sides.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .exposure import ExposureResult, vo_exposure


@dataclass
class TecParams:
    offhire_usd_day: float = 22000.0
    fuel_t_day: float = 44.0        # laden deviation consumption
    fuel_usd_t: float = 580.0       # VLSFO
    speed_kn: float = 12.5          # deviation speed
    growth_default: float = 0.094   # fallback final-account growth

    @property
    def fuel_per_nm(self) -> float:
        return self.fuel_t_day * self.fuel_usd_t / (self.speed_kn * 24.0)


@dataclass
class BidEval:
    bid_id: str
    yard_name: str
    normalized_usd: float           # N
    dock_days: int
    deviation_nm: float = 0.0
    deviation_port_fees: float = 0.0
    excluded_items: list[dict] = field(default_factory=list)
    below_norm_items: list[dict] = field(default_factory=list)
    growth_pct: float | None = None  # None -> params.growth_default
    has_crit_flag: bool = False
    sticker_usd: float | None = None  # raw bid before normalization (for display)


@dataclass
class TecComponents:
    bid_id: str
    yard_name: str
    normalized_usd: float
    deviation_usd: float
    offhire_usd: float
    vo_exposure_usd: float
    deviation_nm: float
    deviation_days: float
    tec_usd: float
    exposure: ExposureResult
    rank: int = 0
    recommended: bool = False
    note: str = ""


def _one(bid: BidEval, params: TecParams) -> TecComponents:
    dev_days = bid.deviation_nm / (params.speed_kn * 24.0) if bid.deviation_nm else 0.0
    deviation = round(bid.deviation_nm * params.fuel_per_nm + bid.deviation_port_fees, 2)
    offhire = round(bid.dock_days * params.offhire_usd_day, 2)
    growth = bid.growth_pct if bid.growth_pct is not None else params.growth_default
    exposure = vo_exposure(
        normalized_usd=bid.normalized_usd,
        excluded_items=bid.excluded_items,
        below_norm_items=bid.below_norm_items,
        growth_pct=growth,
    )
    tec = round(bid.normalized_usd + deviation + offhire + exposure.total_usd, 2)
    return TecComponents(
        bid_id=bid.bid_id,
        yard_name=bid.yard_name,
        normalized_usd=bid.normalized_usd,
        deviation_usd=deviation,
        offhire_usd=offhire,
        vo_exposure_usd=exposure.total_usd,
        deviation_nm=bid.deviation_nm,
        deviation_days=round(dev_days, 2),
        tec_usd=tec,
        exposure=exposure,
    )


def evaluate(bids: list[BidEval], params: TecParams | None = None) -> list[TecComponents]:
    """Compute TEC for every bid, rank by TEC ascending, mark the recommendation."""
    params = params or TecParams()
    comps = [_one(b, params) for b in bids]
    comps.sort(key=lambda c: c.tec_usd)
    for i, c in enumerate(comps, start=1):
        c.rank = i

    # Recommendation: lowest TEC with no crit flag. If the lowest has a crit flag,
    # recommend the next clean bid and explain.
    crit = {b.bid_id for b in bids if b.has_crit_flag}
    recommended = None
    for c in comps:
        if c.bid_id not in crit:
            recommended = c
            break
    if recommended is None:  # all flagged — fall back to lowest TEC
        recommended = comps[0]
    recommended.recommended = True
    if recommended.rank != 1:
        recommended.note = (
            "Lowest TEC carries a critical exposure flag; recommended the next "
            "fully-scoped bid."
        )
    return comps
