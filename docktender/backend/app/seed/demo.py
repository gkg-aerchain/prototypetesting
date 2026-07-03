"""Demo tenant fixtures — Galene Maritime. Builds the 12-vessel fleet, the live
tender TND-2026-014 (M/T Kalymnos Voyager SS No. 2) with three bids calibrated so
the TEC engine computes $2.90M / $3.04M / $3.15M, the agent-event feed, and the
Paros Horizon execution + Milos Beacon settlement that drive the command-center KPIs.

'Today' for the demo is Thursday 3 July 2026 (matches the approved mock).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    AgentEvent,
    Award,
    Bid,
    BidLine,
    Dock,
    Evaluation,
    FinalAccount,
    Invitation,
    Organization,
    Specification,
    SpecItem,
    TecComponent,
    Tender,
    VariationOrder,
    Vessel,
    WorkItem,
    Yard,
    YardScore,
)

DEMO_TODAY = date(2026, 7, 3)


def _dt(d: date) -> datetime:
    return datetime(d.year, d.month, d.day)


# (name, type, dwt, loa, beam, draft, gt, built, class, last_dock, ss_no, uwild, edd, tce)
FLEET = [
    ("Kalymnos Voyager", "LR2", 115000, 250.0, 44.0, 14.9, 63000, 2014, "LR",
     date(2023, 11, 14), 2, True, False, 22000),
    ("Thera Compass", "Aframax", 105000, 248.0, 43.8, 14.7, 58000, 2012, "DNV",
     date(2024, 3, 2), 2, False, False, 19500),
    ("Naxos Meridian", "MR", 49900, 183.0, 32.2, 13.0, 29000, 2016, "ABS",
     date(2024, 6, 19), 4, True, False, 16000),
    ("Paros Horizon", "LR2", 114500, 250.0, 44.0, 14.9, 62800, 2013, "LR",
     date(2021, 6, 20), 1, True, False, 22000),
    ("Milos Beacon", "MR", 49900, 183.0, 32.2, 13.0, 29000, 2015, "ABS",
     date(2021, 6, 12), 3, True, False, 16000),
    ("Sifnos Trader", "MR", 49900, 183.0, 32.2, 13.0, 29000, 2018, "BV",
     date(2024, 9, 10), 2, True, False, 16000),
    ("Serifos Wind", "Aframax", 106000, 249.0, 44.0, 14.8, 58500, 2017, "DNV",
     date(2024, 11, 4), 2, True, True, 19500),
    ("Amorgos Spirit", "MR", 50000, 184.0, 32.3, 13.1, 29200, 2019, "LR",
     date(2025, 1, 22), 1, True, False, 16200),
    ("Folegandros Bay", "LR1", 74000, 228.0, 32.2, 14.0, 42000, 2016, "ABS",
     date(2025, 3, 15), 2, True, False, 18000),
    ("Ikaria Dawn", "MR", 49900, 183.0, 32.2, 13.0, 29000, 2020, "BV",
     date(2025, 5, 30), 1, True, False, 16000),
    ("Skyros Light", "Aframax", 105500, 248.5, 43.9, 14.7, 58200, 2015, "DNV",
     date(2025, 8, 12), 2, True, False, 19500),
    ("Andros Pioneer", "LR2", 114800, 250.0, 44.0, 14.9, 63000, 2018, "LR",
     date(2025, 10, 3), 1, True, True, 22000),
]

# The 3 leveling bids, calibrated to the engine (see test_tec.py).
BID_SPECS = [
    dict(yard="Drydocks World — Dubai", dock="Dock 2", currency="USD", sticker=2_410_000,
         normalized=2_410_000, dock_days=13, slot=(date(2026, 10, 28), date(2026, 11, 10)),
         tariff=True, deviation_nm=420, port_fees=60_000, growth_pct=0.045, crit=False,
         excluded=[], below_norm=[],
         note="Complete bid. All 312 lines priced, standard tariff annexed, lowest VO "
              "exposure. On-route deviation only 420 nm."),
    dict(yard="Seatrium Admiralty Yard", dock="Dock 1", currency="USD", sticker=2_520_000,
         normalized=2_520_000, dock_days=12, slot=(date(2026, 10, 21), date(2026, 11, 2)),
         tariff=True, deviation_nm=1890, port_fees=0, growth_pct=0.013, crit=False,
         excluded=[{"label": "Boiler retube 42 tubes", "median_usd": 206_500}],
         below_norm=[],
         note="Strong yard, long deviation. Fastest dock time; 1,890 nm off-route from "
              "the Fujairah discharge adds $162k steaming."),
    dict(yard="Besiktas Shipyard (Yalova)", dock="Floating Dock 1", currency="USD", sticker=2_190_000,
         normalized=2_190_000, dock_days=16, slot=(date(2026, 10, 25), date(2026, 11, 10)),
         tariff=False, deviation_nm=2572, port_fees=0, growth_pct=0.094, crit=True,
         excluded=[{"label": "Grit disposal", "median_usd": 18_000},
                   {"label": "Class attendance fees", "median_usd": 16_000},
                   {"label": "Staging", "median_usd": 42_000},
                   {"label": "Cargo tank cleaning", "median_usd": 55_000},
                   {"label": "Sea-chest anodes", "median_usd": 22_000},
                   {"label": "Misc owner works", "median_usd": 25_000}],
         standalone_exclusions=[{"label": "Grit disposal"}, {"label": "Class attendance fees"},
                                {"label": "Staging"}, {"label": "Cargo tank cleaning"},
                                {"label": "Sea-chest anodes"}, {"label": "Misc owner works"}],
         below_norm=[{"label": "Steel renewal 104 mh/t below norm on TBC quantity",
                      "extra_usd": 130_000}],
         note="Cheapest bid, highest exposure. Grit disposal and staging excluded; "
              "below-norm steel on a to-be-confirmed quantity — the classic "
              "final-account growth pattern."),
]

# Section totals per bid (drives the leveling matrix; best marked in the engine layer).
SECTION_MATRIX = [
    # (section_name, code_hint, dubai, sembcorp, besiktas, besiktas_flag)
    ("General services", "§1 · 22 lines", 318_400, 342_100, 296_750, "Grit disposal excluded"),
    ("Hull treatment", "§2 · 12,400 m² · Sa 2.5 spot 30%", 486_200, 471_900, 438_300, "−9% vs low norm band"),
    ("Steel renewals", "§3 · 48.2 t est · qty TBC", 561_500, 602_800, 402_100, "104 mh/t · −48% vs norm"),
    ("Sea valves & overboard", "§4 · 14 valves", 128_900, 119_400, 131_200, None),
    ("Tail shaft survey", "§5 · keyless · class witnessed", 96_300, 104_750, 92_000, "Class fees excluded"),
    ("Boiler & economizer", "§6 · retube 42 tubes", 214_600, None, 198_400, None),
]


def seed_demo_data(db: Session, org: Organization) -> None:
    """Idempotent: skips if the demo tender already exists."""
    if db.scalar(select(Tender).where(Tender.ref == "TND-2026-014")):
        return

    # ---- fleet
    vessels: dict[str, Vessel] = {}
    for (name, vtype, dwt, loa, beam, draft, gt, built, cls, last, ssno, uw, edd, tce) in FLEET:
        v = Vessel(
            org_id=org.id, name=name, vessel_type=vtype, dwt=dwt, loa_m=loa, beam_m=beam,
            summer_draft_m=draft, gt=gt, built_year=built, class_society=cls,
            last_docking_date=_dt(last), special_survey_no=ssno, uwild_ok=uw,
            edd_enrolled=edd, tce_usd_day=tce,
        )
        db.add(v)
        db.flush()
        vessels[name] = v

    kalymnos = vessels["Kalymnos Voyager"]

    # ---- specification for the live tender (frozen), 312 lines
    spec = Specification(
        org_id=org.id, vessel_id=kalymnos.id,
        title="Kalymnos Voyager — SS No. 2 docking specification",
        docking_window_start=_dt(date(2026, 7, 17)),
        docking_window_end=_dt(date(2026, 11, 14)),
        status="frozen", version=1, frozen_at=_dt(date(2026, 6, 10)),
    )
    db.add(spec)
    db.flush()
    _build_spec_items(db, spec)

    # ---- tender + invitations
    tender = Tender(
        org_id=org.id, spec_id=spec.id, ref="TND-2026-014", status="issued",
        deadline=_dt(date(2026, 7, 10)), fx_date=_dt(date(2026, 7, 1)),
        fx_rates_json={"EUR": 1.08, "SGD": 0.74, "AED": 0.27, "TRY": 0.031},
        offhire_usd_day=22000, sealed=True,
    )
    db.add(tender)
    db.flush()

    # ---- bids
    section_items = _spec_items_by_section(db, spec)
    bid_rows: list[Bid] = []
    for bspec in BID_SPECS:
        yard = _match_yard(db, bspec["yard"])
        dock = _match_dock(db, yard, bspec["dock"]) if yard else None
        db.add(Invitation(tender_id=tender.id, yard_id=yard.id if yard else "", status="bid_received"))
        bid = Bid(
            tender_id=tender.id, yard_id=yard.id if yard else "", revision=1,
            currency=bspec["currency"], validity_date=_dt(date(2026, 8, 15)),
            dock_id=dock.id if dock else None, dock_days=bspec["dock_days"],
            slot_start=_dt(bspec["slot"][0]), slot_end=_dt(bspec["slot"][1]),
            terms_json={"note": bspec["note"]}, tariff_captured=bspec["tariff"],
            sealed_until=_dt(date(2026, 7, 10)), source="portal",
        )
        db.add(bid)
        db.flush()
        bid_rows.append(bid)
        _build_bid_lines(db, bid, bspec, section_items)

    # A fourth yard was invited to Kalymnos but has not bid -> "3 of 4 bids in".
    fourth = _match_yard(db, "Oman Drydock Company (Duqm)")
    if fourth:
        db.add(Invitation(tender_id=tender.id, yard_id=fourth.id, status="invited"))

    # ---- evaluation + TEC components (computed by the engine)
    _build_evaluation(db, tender, bid_rows)

    # ---- Thera Compass: tender out, 7 invited (no bids yet)
    _build_thera_tender(db, org, vessels["Thera Compass"])

    # ---- Naxos Meridian: spec 40% drafted (no tender yet)
    _build_naxos_draft(db, org, vessels["Naxos Meridian"])

    # ---- Paros Horizon execution (in dock, 2 VOs open) + award
    _build_paros_execution(db, org, vessels["Paros Horizon"])

    # ---- Milos Beacon settlement (final account, +9.4% growth)
    _build_milos_settlement(db, org, vessels["Milos Beacon"])

    # ---- yard scorecards (history that also feeds growth defaults)
    _build_yard_scores(db)

    # ---- agent-event feed + review queue
    _build_agent_events(db, org, kalymnos, vessels["Naxos Meridian"], vessels["Paros Horizon"])

    db.flush()


# --------------------------------------------------------------------------- helpers
def _match_yard(db: Session, name: str) -> Yard | None:
    key = name.replace("—", "-")
    # exact match first
    for y in db.scalars(select(Yard)):
        if y.name.replace("—", "-") == key:
            return y
    # else a distinctive substring match (e.g. "ASRY", "Colombo Dockyard")
    for y in db.scalars(select(Yard)):
        if key in y.name.replace("—", "-"):
            return y
    return None


def _match_dock(db: Session, yard: Yard, dock_name: str) -> Dock | None:
    for d in db.scalars(select(Dock).where(Dock.yard_id == yard.id)):
        if d.name == dock_name:
            return d
    return next(iter(db.scalars(select(Dock).where(Dock.yard_id == yard.id))), None)


def _build_spec_items(db: Session, spec: Specification) -> None:
    """Create 312 spec lines: pull the full library for §1-§6 and a slice of §7-§10,
    repeating typical items with varied quantities to reach 312 realistic lines."""
    work_items = list(db.scalars(select(WorkItem).order_by(WorkItem.section, WorkItem.code)))
    by_section: dict[int, list[WorkItem]] = {}
    for wi in work_items:
        by_section.setdefault(wi.section, []).append(wi)

    line_no = 0
    target = 312
    # weight sections 1-6 heavily (the docking-critical scope), lighter 7-10
    plan = {1: 46, 2: 44, 3: 40, 4: 26, 5: 30, 6: 22, 7: 34, 8: 40, 9: 20, 10: 10}
    steel_tbc_code = "ST-001"
    for section, count in plan.items():
        items = by_section.get(section, [])
        if not items:
            continue
        for i in range(count):
            wi = items[i % len(items)]
            line_no += 1
            qty = _demo_qty(wi, i)
            tbc = wi.code == steel_tbc_code
            db.add(SpecItem(
                spec_id=spec.id, work_item_id=wi.id, line_no=line_no, title=wi.title,
                qty=qty, uom=wi.uom, qty_tbc=tbc,
                origin="class" if section in (3, 5, 10) else "owner",
                notes="Quantity to be confirmed on inspection" if tbc else "",
            ))
            if line_no >= target:
                return


def _demo_qty(wi: WorkItem, i: int) -> float:
    if wi.uom == "m2":
        return 12400 if wi.code == "HT-003" else round(200 + i * 37.5, 1)
    if wi.uom == "t":
        return 48.2 if wi.code == "ST-001" else round(2 + i * 1.5, 1)
    if wi.uom in ("day", "shift", "hr"):
        return 13
    if wi.uom in ("ea", "tube", "valve", "blade", "cyl", "point", "set", "shackle"):
        return (i % 6) + 1
    return round(1 + i, 1)


def _spec_items_by_section(db: Session, spec: Specification) -> dict[int, list[SpecItem]]:
    out: dict[int, list[SpecItem]] = {}
    items = db.scalars(select(SpecItem).where(SpecItem.spec_id == spec.id))
    wi_section = {wi.id: wi.section for wi in db.scalars(select(WorkItem))}
    for si in items:
        sec = wi_section.get(si.work_item_id, 0)
        out.setdefault(sec, []).append(si)
    return out


def _build_bid_lines(db: Session, bid: Bid, bspec: dict, section_items: dict[int, list[SpecItem]]) -> None:
    """Create bid lines whose section subtotals match SECTION_MATRIX and whose grand
    total equals the bid's normalized figure. One representative priced line per
    section carries that section's subtotal; excluded/unpriced items are flagged."""
    col = {"Drydocks World — Dubai": 2, "Seatrium Admiralty Yard": 3,
           "Besiktas Shipyard (Yalova)": 4}[bspec["yard"]]
    priced_total = 0.0
    section_no = 0
    for (sec_name, _hint, dubai, semb, bes, bes_flag) in SECTION_MATRIX:
        section_no += 1
        amount = (dubai, semb, bes)[col - 2]
        items = section_items.get(section_no, [])
        target_item = items[0] if items else None
        # The section flag only applies to the Besiktas column (col 4).
        flag = bes_flag if col == 4 else None
        if amount is None:
            # unpriced (Sembcorp boiler)
            db.add(BidLine(
                bid_id=bid.id, spec_item_id=target_item.id if target_item else None,
                raw_text=sec_name, uom="lot", state="unpriced",
                assumptions=flag or "Priced on inspection",
            ))
            continue
        db.add(BidLine(
            bid_id=bid.id, spec_item_id=target_item.id if target_item else None,
            raw_text=sec_name, uom="lot", amount=float(amount), state="priced",
            assumptions=flag or "",
        ))
        priced_total += amount
    # remainder line to reach the bid's normalized total (other sections §7-§10)
    remainder = round(bspec["normalized"] - priced_total, 2)
    if abs(remainder) > 0.01:
        db.add(BidLine(
            bid_id=bid.id, spec_item_id=None, raw_text="Sections §7–§10 (machinery, piping, class)",
            uom="lot", amount=remainder, state="priced",
        ))
    # Standalone exclusion lines (sub-items excluded from scope, not whole sections).
    # An item that is an unpriced *section* (e.g. Sembcorp's boiler) is represented by
    # its unpriced section line above, not duplicated here.
    for exc in bspec.get("standalone_exclusions", []):
        db.add(BidLine(
            bid_id=bid.id, spec_item_id=None, raw_text=exc["label"], state="excluded",
            assumptions="Excluded from bid scope",
        ))


def _build_evaluation(db: Session, tender: Tender, bids: list[Bid]) -> None:
    from ..engines.tec import BidEval, TecParams, evaluate

    params = TecParams(offhire_usd_day=tender.offhire_usd_day)
    yard_name = {b.id: _yard_name(db, b.yard_id) for b in bids}
    evals = []
    for bid, bspec in zip(bids, BID_SPECS):
        evals.append(BidEval(
            bid_id=bid.id, yard_name=yard_name[bid.id], normalized_usd=bspec["normalized"],
            dock_days=bspec["dock_days"], deviation_nm=bspec["deviation_nm"],
            deviation_port_fees=bspec["port_fees"], excluded_items=bspec["excluded"],
            below_norm_items=bspec["below_norm"], growth_pct=bspec["growth_pct"],
            has_crit_flag=bspec["crit"], sticker_usd=bspec["sticker"],
        ))
    comps = evaluate(evals, params)

    ev = Evaluation(tender_id=tender.id, params_json={
        "offhire_usd_day": params.offhire_usd_day, "fuel_t_day": params.fuel_t_day,
        "fuel_usd_t": params.fuel_usd_t, "speed_kn": params.speed_kn,
        "growth_default": params.growth_default,
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


def _yard_name(db: Session, yard_id: str) -> str:
    y = db.get(Yard, yard_id) if yard_id else None
    return y.name if y else ""


def _build_thera_tender(db: Session, org: Organization, thera: Vessel) -> None:
    """Thera Compass — tender issued to 7 yards, no bids received yet."""
    spec = Specification(org_id=org.id, vessel_id=thera.id,
                         title="Thera Compass — IS + UWILD docking specification",
                         docking_window_start=_dt(date(2026, 11, 2)),
                         docking_window_end=_dt(date(2027, 3, 2)),
                         status="frozen", version=1, frozen_at=_dt(date(2026, 6, 20)))
    db.add(spec)
    db.flush()
    tender = Tender(org_id=org.id, spec_id=spec.id, ref="TND-2026-015", status="issued",
                    deadline=_dt(date(2026, 8, 20)), offhire_usd_day=19500, sealed=True)
    db.add(tender)
    db.flush()
    invited = ["Drydocks World", "Seatrium Admiralty", "ASRY", "Oman Drydock",
               "N-KOM", "Colombo Dockyard", "Besiktas"]
    for key in invited:
        yard = _match_yard(db, key)
        if yard:
            db.add(Invitation(tender_id=tender.id, yard_id=yard.id, status="invited"))


def _build_naxos_draft(db: Session, org: Organization, naxos: Vessel) -> None:
    """Naxos Meridian — specification in draft (40% complete), no tender yet."""
    spec = Specification(org_id=org.id, vessel_id=naxos.id,
                         title="Naxos Meridian — SS No. 4 docking specification",
                         docking_window_start=_dt(date(2027, 2, 19)),
                         docking_window_end=_dt(date(2027, 6, 19)),
                         status="draft", version=1)
    db.add(spec)
    db.flush()
    tender = Tender(org_id=org.id, spec_id=spec.id, ref="TND-2026-016", status="draft",
                    offhire_usd_day=16000, sealed=True)
    db.add(tender)


def _build_paros_execution(db: Session, org: Organization, paros: Vessel) -> None:
    """Paros Horizon is in dock (day 6/13) with 7 VOs, 2 open. Needs an award to hang
    the VOs off — create a minimal awarded tender for her previous docking."""
    spec = Specification(org_id=org.id, vessel_id=paros.id,
                         title="Paros Horizon — SS No. 1 docking specification",
                         status="frozen", version=1, frozen_at=_dt(date(2026, 5, 1)))
    db.add(spec)
    db.flush()
    tender = Tender(org_id=org.id, spec_id=spec.id, ref="TND-2026-009", status="awarded",
                    deadline=_dt(date(2026, 5, 10)), offhire_usd_day=22000, sealed=False)
    db.add(tender)
    db.flush()
    yard = _match_yard(db, "ASRY")
    bid = Bid(tender_id=tender.id, yard_id=yard.id if yard else "", currency="USD",
              dock_days=13, tariff_captured=True, source="portal",
              slot_start=_dt(date(2026, 6, 28)), slot_end=_dt(date(2026, 7, 10)))
    db.add(bid)
    db.flush()
    award = Award(tender_id=tender.id, bid_id=bid.id, memo_note="Awarded to ASRY on TEC.",
                  checklist_json={"tariff_annexed": True, "validity": True, "dock_confirmed": True},
                  awarded_at=_dt(date(2026, 5, 12)))
    db.add(award)
    db.flush()
    vos = [
        ("VO-01", "Additional shell plate — fwd ballast tank", 4, "t", 14800, "§3.2", 14200, "approved"),
        ("VO-02", "Extra staging — under-deck access", 120, "m3", 2160, "§1.16", 2160, "approved"),
        ("VO-03", "Sea-chest grid renewal (found wasted)", 2, "ea", 3400, "§4.6", 3400, "approved"),
        ("VO-04", "Rudder pintle re-bush", 1, "lot", 9800, "§5.3", 9200, "approved"),
        ("VO-05", "Cargo pump mechanical seal", 2, "ea", 5600, None, None, "approved"),
        ("VO-06", "Additional anodes — 12 pcs", 12, "ea", 11840, "§4.2", 11840, "approved"),
        ("VO-07", "Sea valve seat re-facing", 1, "ea", 8100, "§4.1", 4000, "proposed"),
    ]
    for (no, title, qty, uom, proposed, ref, tariff, state) in vos:
        db.add(VariationOrder(
            org_id=org.id, award_id=award.id, vo_no=no, title=title, qty=qty, uom=uom,
            proposed_usd=proposed, tariff_line_ref=ref, tariff_usd=tariff, state=state,
            decided_by="S. Nair" if state == "approved" else None,
            decided_at=_dt(date(2026, 6, 30)) if state == "approved" else None,
        ))
    # a second open VO to reach "2 VOs open"
    db.add(VariationOrder(
        org_id=org.id, award_id=award.id, vo_no="VO-08", title="Bilge keel crop & renew — 6 m",
        qty=6, uom="m", proposed_usd=7200, tariff_line_ref=None, tariff_usd=None, state="proposed",
    ))


def _build_milos_settlement(db: Session, org: Organization, milos: Vessel) -> None:
    spec = Specification(org_id=org.id, vessel_id=milos.id,
                         title="Milos Beacon — SS No. 3 docking specification",
                         status="frozen", version=1, frozen_at=_dt(date(2026, 4, 1)))
    db.add(spec)
    db.flush()
    tender = Tender(org_id=org.id, spec_id=spec.id, ref="TND-2026-006", status="awarded",
                    deadline=_dt(date(2026, 4, 10)), offhire_usd_day=16000, sealed=False)
    db.add(tender)
    db.flush()
    yard = _match_yard(db, "Colombo Dockyard")
    bid = Bid(tender_id=tender.id, yard_id=yard.id if yard else "", currency="USD",
              dock_days=11, tariff_captured=True, source="portal")
    db.add(bid)
    db.flush()
    award = Award(tender_id=tender.id, bid_id=bid.id, memo_note="Awarded to Colombo Dockyard.",
                  awarded_at=_dt(date(2026, 4, 12)))
    db.add(award)
    db.flush()
    quoted = 1_840_000.0
    final = 2_012_960.0  # +9.4%
    db.add(FinalAccount(
        award_id=award.id, quoted_usd=quoted, final_usd=final,
        growth_pct=round((final / quoted - 1) * 100, 1),
        lines_json=[
            {"section": "Contract price", "quoted": quoted, "final": quoted},
            {"section": "Approved variations", "quoted": 0, "final": round(final - quoted, 2)},
        ],
        closed_at=_dt(date(2026, 6, 12)),
    ))


def _build_yard_scores(db: Session) -> None:
    data = [
        ("Colombo Dockyard", "TND-2026-006", 9.4, 1, 4, 4),
        ("ASRY", "TND-2025-041", 6.1, 0, 4, 5),
        ("Drydocks World", "TND-2025-022", 5.2, 0, 5, 4),
        ("Sembcorp", "TND-2025-019", 4.8, 1, 5, 5),
        ("Besiktas", "TND-2024-033", 14.7, 3, 3, 3),
    ]
    for (yard_key, ref, growth, overrun, quality, hse) in data:
        yard = _match_yard(db, yard_key)
        if yard:
            db.add(YardScore(yard_id=yard.id, docking_ref=ref, growth_pct=growth,
                             overrun_days=overrun, quality=quality, hse=hse))


def _build_agent_events(db, org, kalymnos, naxos, paros) -> None:
    events = [
        ("bid_parser", "info", kalymnos.id,
         "Besiktas quotation ingested — 82 lines mapped, 6 exclusions detected.",
         "BID-0192 · 78/82 high confidence", True),
        ("sanity_checker", "warn", kalymnos.id,
         "Besiktas steel at 104 mh/t — 48% below guide norm for 12.5 mm shell plate.",
         "Norm 230 mh/t · Butler T3.1", False),
        ("docking_clock", "warn", naxos.id,
         "Naxos Meridian enters her 36-month window in 89 days — spec is 40% drafted.",
         "", False),
        ("vo_reconciler", "info", paros.id,
         "Paros Horizon VO-06 matches captured tariff — cleared for approval.",
         "Tariff §4.2 · $11,840", False),
        ("vo_reconciler", "warn", paros.id,
         "VO-07 sea valve seat — $4,100 over captured tariff.",
         "Tariff §4.1 · quoted $8,100 vs $4,000", True),
        ("clarifier", "info", kalymnos.id,
         "3 clarification questions drafted from bid exclusions.",
         "Thera Compass · awaiting review", True),
    ]
    base = datetime(2026, 7, 3, 9, 0)
    for i, (agent, sev, vid, msg, ev, needs) in enumerate(events):
        db.add(AgentEvent(
            org_id=org.id, agent=agent, severity=sev, vessel_id=vid, message=msg,
            evidence=ev, needs_decision=needs, ts=base - timedelta(hours=i),
        ))
