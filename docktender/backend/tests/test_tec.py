"""TEC engine calibration — the demo tender must compute to the approved mock figures:
Drydocks Dubai $2.90M / Seatrium (Sembcorp) Admiralty $3.04M / Besiktas $3.15M, with
Dubai ranked 1 and recommended, Besiktas last."""
from app.engines.tec import BidEval, TecParams, evaluate


def _demo_bids():
    return [
        BidEval("dubai", "Drydocks World — Dubai", 2_410_000, 13, deviation_nm=420,
                deviation_port_fees=60_000, excluded_items=[], growth_pct=0.045,
                has_crit_flag=False, sticker_usd=2_410_000),
        BidEval("sembcorp", "Seatrium Admiralty Yard", 2_520_000, 12, deviation_nm=1890,
                deviation_port_fees=0,
                excluded_items=[{"label": "Boiler retube 42 tubes", "median_usd": 206_500}],
                growth_pct=0.013, has_crit_flag=False, sticker_usd=2_520_000),
        BidEval("besiktas", "Besiktas Shipyard (Yalova)", 2_190_000, 16, deviation_nm=2572,
                deviation_port_fees=0,
                excluded_items=[{"label": "Grit disposal", "median_usd": 18_000},
                                {"label": "Class fees", "median_usd": 16_000},
                                {"label": "Staging", "median_usd": 42_000},
                                {"label": "Tank cleaning", "median_usd": 55_000},
                                {"label": "Anodes", "median_usd": 22_000},
                                {"label": "Misc", "median_usd": 25_000}],
                below_norm_items=[{"label": "Steel below norm on TBC", "extra_usd": 130_000}],
                growth_pct=0.094, has_crit_flag=True, sticker_usd=2_190_000),
    ]


def test_tec_hits_mock_targets():
    comps = {c.bid_id: c for c in evaluate(_demo_bids(), TecParams(offhire_usd_day=22000))}
    assert abs(comps["dubai"].tec_usd - 2_900_000) <= 10_000
    assert abs(comps["sembcorp"].tec_usd - 3_040_000) <= 10_000
    assert abs(comps["besiktas"].tec_usd - 3_150_000) <= 10_000


def test_ranks_and_recommendation():
    comps = evaluate(_demo_bids(), TecParams(offhire_usd_day=22000))
    by_id = {c.bid_id: c for c in comps}
    assert by_id["dubai"].rank == 1
    assert by_id["sembcorp"].rank == 2
    assert by_id["besiktas"].rank == 3
    # Dubai is the lowest TEC with no crit flag -> recommended
    assert by_id["dubai"].recommended is True
    assert by_id["besiktas"].recommended is False


def test_sticker_trap_besiktas_lowest_sticker_highest_tec():
    """The product thesis: cheapest sticker is the most expensive once exposure is priced."""
    comps = {c.bid_id: c for c in evaluate(_demo_bids(), TecParams(offhire_usd_day=22000))}
    # Besiktas has the lowest sticker...
    stickers = {b.bid_id: b.sticker_usd for b in _demo_bids()}
    assert stickers["besiktas"] == min(stickers.values())
    # ...but the highest TEC.
    assert comps["besiktas"].tec_usd == max(c.tec_usd for c in comps.values())


def test_off_hire_scales_with_dock_days():
    comps = {c.bid_id: c for c in evaluate(_demo_bids(), TecParams(offhire_usd_day=22000))}
    assert comps["dubai"].offhire_usd == 13 * 22000
    assert comps["besiktas"].offhire_usd == 16 * 22000


def test_recommendation_skips_crit_when_lowest():
    """If the lowest TEC carries a crit flag, the next clean bid is recommended."""
    bids = _demo_bids()
    # Force Dubai to be cheapest but critically flagged.
    bids[0].has_crit_flag = True
    comps = evaluate(bids, TecParams(offhire_usd_day=22000))
    rec = next(c for c in comps if c.recommended)
    assert rec.bid_id == "sembcorp"  # next clean bid by TEC
    assert rec.note  # carries an explanation
