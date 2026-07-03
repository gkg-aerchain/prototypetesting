"""VO-exposure model — the itemized risk that backs the TEC's exposure term and the
"Open exposure model" drawer. Exposure is what the sticker price hides: work a yard
excluded or left unpriced (which you will pay as a variation, at a premium), plus the
statistical final-account growth a bid carries given its completeness and tariff status.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# A yard prices uncontracted (variation) work above the competitive tender price;
# this premium is the exposure on an excluded/unpriced item vs a complete bid that
# already priced it. (The base cost is a wash — you pay it either way.)
VO_PREMIUM = 0.30


@dataclass
class ExposureItem:
    label: str
    kind: str            # excluded|unpriced|below_norm|growth
    basis_usd: float     # the median/reference value the risk is computed from
    exposure_usd: float  # the modelled exposure contribution


@dataclass
class ExposureResult:
    total_usd: float
    items: list[ExposureItem] = field(default_factory=list)


def vo_exposure(
    *,
    normalized_usd: float,
    excluded_items: list[dict],   # [{label, median_usd}]
    growth_pct: float,            # assumed final-account growth for this bid
    below_norm_items: list[dict] | None = None,  # [{label, extra_usd}]
    vo_premium: float = VO_PREMIUM,
) -> ExposureResult:
    """Compute itemized VO exposure for a single bid.

    - excluded_items: work excluded or left unpriced; exposure = median x premium.
    - below_norm_items: extra cost risk when a below-norm rate meets a TBC quantity.
    - growth: growth_pct x normalized bid (universal final-account creep, higher for
      bids with no tariff annexed / below-norm rates).
    """
    items: list[ExposureItem] = []
    for it in excluded_items:
        med = float(it["median_usd"])
        items.append(ExposureItem(it["label"], it.get("kind", "excluded"), med, round(med * vo_premium, 2)))
    for it in (below_norm_items or []):
        extra = float(it["extra_usd"])
        items.append(ExposureItem(it["label"], "below_norm", extra, round(extra, 2)))
    growth = round(growth_pct * normalized_usd, 2)
    items.append(ExposureItem(
        f"Final-account growth ({growth_pct * 100:.1f}%)", "growth", normalized_usd, growth
    ))
    total = round(sum(i.exposure_usd for i in items), 2)
    return ExposureResult(total_usd=total, items=items)
