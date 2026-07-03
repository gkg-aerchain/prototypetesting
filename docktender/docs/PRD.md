# DockTender — Product Requirements Document

**Two-sided dry-docking procurement: specification → tender → normalized bid analysis → award → variation-order control → final account.**

Version 0.1 · July 2026 · Research-grounded (all domain claims below are source-verified; citations at end)

---

## 1. The problem

Every commercial ship must put its bottom out of the water on a fixed regulatory clock: **two bottom inspections in each 5-year special-survey period, never more than 36 months apart** (SOLAS Reg I/10(a)(v) + class rules) [1]. One of the two can often be replaced by an in-water survey (UWILD) for ships generally under 15 years [2], and qualifying vessels on Extended Dry-Docking schemes stretch to ~7.5 years between dockings (IACS Rec. 133; UK MGN 672(M)) [3] — but the docking event itself is unavoidable, expensive (typically USD 0.5–3M+ per event), and procured under time pressure against the survey deadline.

The procurement itself is broken in a specific, well-understood way:

- **The manager** sends the same specification to 3–6 yards near the trading route and receives back quotations that "always vary tremendously" — not only because yards differ in efficiency, but because each yard applies a **commercial variance factor** on top of its man-hour build-up, reflecting local economy, current workload, and how hungry it is for work [9]. Quotes arrive in different currencies, different line groupings, different units (lump sum vs per-tonne vs per-m² vs per-day), with different inclusions — so like-for-like comparison is a **normalization problem**, not a spreadsheet diff. Today it is done by hand, in Excel, by a docking superintendent, over days.
- **The cheapest bid is routinely not the cheapest docking.** Deviation steaming, off-hire days, and the yard's appetite for variation-order growth (unpriced extras: blasting-grit removal, keel/side-block shifting for access, tank cleaning) can invert the ranking [6][10].
- **The yard** prices bottom-up from a standing tariff book — man-hour norms per work item × labour rate, per-m² hull treatment rates, itemized general services — then adjusts commercially per customer and slot pressure. Repeat customers price differently from first-timers. This estimating expertise lives in a department's heads and spreadsheets.

## 2. Positioning & the honest competitive gap

**What already exists (do not claim otherwise — an expert will know):**

| Product | Verified capability | Deployment |
|---|---|---|
| **MariApps smartPAL Drydock** | Multi-currency tender & quote comparison; defect-jobs → docking-spec workflow; integrated with smartPAL procurement/accounts [11] | Owner-side module in a fleet-management ERP |
| **BASSnet Docking / Projects** | Onboard spec drafting by crew; standard work-item template libraries; spec reuse; RFQ dispatch, quote comparison, yard grading, "Yard Bid Report". Live at Wilhelmsen SM, Wallem, OSM Thome, Anthony Veder [12] | Owner-side module in a fleet-management ERP |
| Maindeck, DockPlan, Shipnet, ABS Wavesight | Spec templates / docking project tools (surfaced during verification; not exhaustively verified) | Owner-side |
| Procureship, ShipServ, Moscord | Marine procurement marketplaces for spares/services (not verified as dry-dock tender platforms) | Marketplace, different category |
| Excel + email | The actual incumbent at most managers | — |

**The verified gap DockTender targets** [13]:

1. **Two-sided.** Every verified incumbent is a single-tenant owner-side module. None is a marketplace where yards maintain a structured presence (dock particulars, tariff books, availability) and respond to tenders natively.
2. **AI bid normalization.** None documents automatic mapping of heterogeneous yard quotations (PDF/Excel, lump sums, mixed units, mixed currency, buried exclusions) onto a canonical work-item taxonomy. This is the single highest-value feature: it converts a week of superintendent Excel work into minutes and makes every downstream analytic possible.
3. **Total Evaluated Cost (TEC).** None documents bid + deviation cost + off-hire + VO-risk exposure as a single ranked figure. We can compute deviation distance/fuel with a real routing engine (PassagePilot's router is reusable as a service).
4. **Tariff capture → VO discipline.** The contractual playbook — obtain the yard's standard tariff before contract; agree that extras price per that tariff; agree conditions of contract before award [10] — encoded as workflow, so the final-account fight is won at tender time.

**Positioning sentence:** *DockTender is the tender room for dry-docking: managers run scrutable, normalized, total-cost tenders; yards submit structured bids once instead of re-typing PDFs; both sides settle variation orders against tariffs captured before award.*

## 3. Users & personas

**Buyer side (Phase 1):**
- **Docking / Technical Superintendent** — owns the spec, runs the tender, attends the docking, fights the final account. Primary daily user.
- **Fleet / Technical Manager** — approves award recommendation, watches budget vs actual across the fleet's docking programme.
- **Vessel crew (contributor)** — feeds defect lists and onboard measurements into the spec (BASSnet proved this workflow matters [12]).

**Seller side (Phase 2/3):**
- **Yard Commercial Manager / Estimator** — receives the requirement package, scopes, prices from the tariff book with the commercial variance factor, submits and negotiates the bid.
- **Yard Planner** — dock slot occupancy, block plan, trade workload.

## 4. Domain model (the part that must survive expert scrutiny)

### 4.1 Docking programme drivers
- Vessel record carries: last bottom inspections (dates, in-water or dry), special survey cycle dates, EDD enrolment (with eligibility rules: enrol before age 10; excluded: passenger, ESP tankers/bulkers, UR Z7.1, thruster-fitted, keyed-taper propeller, HSC; mandatory docking at 15 yrs) [3], UWILD eligibility (Administration acceptance, generally <15 yrs) [2].
- Planner computes the **docking window** (latest = last docking + 36 months, hard stop) and drives the tender timeline backwards from it (spec freeze → RFQ out → bids due → award → arrival).

### 4.2 The specification (requirement package)
Sections mirror how yards and superintendents actually structure the document:
1. **General Services** — the ancillary block every bid contains: docking/undocking & dock rent (per day, market-variable), wharfage (per metre LOA), cranage (by crane size), fire/safety watchman (8 mh/shift), garbage skip (per day), shore power connect/disconnect (4–5 mh) + consumption per kWh, fire main connection + daily pressure, gas-free testing + certificate (8–10 mh), staging, tugs/pilotage in-out [7][8].
2. **Dry-dock & hull** — blasting/washing and coating **per m²** by treatment grade (spot/sweep/full; Sa specifications), anodes, marks & draft marks (fixed price), sea chests & gratings, hull openings.
3. **Steel renewals** — **per tonne** with thickness bands and location/curvature context (see 4.3), minimum-quantity threshold behaviour.
4. **Piping** — renewals/repairs per spool/DN, sea valves overhaul (unit).
5. **Machinery** — tail shaft survey (keyed/keyless), propeller polish/repair, rudder clearances/pintles, thrusters, boiler/economizer, coolers.
6. **Class / survey items** — special survey scope, thickness gauging (per point/percentage), UWILD-related items, anchor & cable ranging/calibration.
7. **Electrical**, 8. **Accommodation/outfitting**, 9. **Owner's items** (upgrades, BWTS retrofit-type projects), 10. **Yard general terms** (conditions of contract, payment, guarantee).

Each work item: canonical code, title, description, location on vessel, **unit of measure (lump / per-t / per-m² / per-day / per-unit / mh)**, estimated quantity, attachments (photos, gauging reports), origin (class-required / defect / owner), and *"quantity to be confirmed on inspection"* flag — the classic VO seed.

### 4.3 Estimating norms (benchmark layer)
Encode Butler-style man-hour norms as the neutral benchmark for sanity-checking bids [4][5]:
- **Steel:** 250 mh/t (≤6 mm) sliding to 200 mh/t (20 mm); × curvature (single 1.2 / double 1.3); × location (keel 1.4, garboard/bilge strake 1.25, deck 1.15); +10% high-tensile AH; ~5 t minimum-quantity threshold below which up to double tariff applies [5].
- **Hull treatment:** quoted per m², inclusive of labour/equipment/consumables/cleanup — flag bids where grit removal or sea-growth disposal is excluded (known invoice-inflation vector) [6].
- **Blocks:** keel block shift 5–20 mh by DWT band (<20k=5; 20–100k=10; 100–200k=16; >200k=20), side blocks 3–12 — the canonical "extra" [10].
These norms are *benchmarks for owner-side checking*, not asserted yard tariffs — the UI must say so (expert credibility).

### 4.4 Bid & normalization model
A bid = header (currency, validity, dock offered + dates, payment terms, conditions-of-contract reference, tariff book attached?) + lines. Each line maps to spec item(s) with: unit of measure, quantity, rate, lump sum, **inclusion/exclusion flags**, assumptions, and *unpriced-exposure* markers (items the yard priced "TBA on inspection" or omitted). Normalization output: every yard on the same canonical grid, FX-normalized, with an **exclusions diff** and an **unpriced-exposure list priced provisionally from the yard's captured tariff** — because that is exactly where final accounts blow up [9][10].

### 4.5 Total Evaluated Cost
`TEC = normalized bid total + deviation cost (extra distance to/from yard × fuel + time, via routing engine) + off-hire cost (days quoted + risk buffer × daily hire/TCE) + VO-risk exposure (unpriced items priced at captured tariff × yard growth factor from history) ± owner-supplied adjustments`. Rank bids by TEC, not sticker price.

### 4.6 Execution & settlement
Award → contract checklist (tariff annexed? conditions agreed? guarantee terms?) [10] → daily VO log during docking (each VO priced against captured tariff, approved/disputed states) → final account reconciliation (quoted vs final, growth %) → **yard scorecard** (price growth %, schedule overrun days, quality/rework, HSE) feeding the next tender's TEC risk factor.

## 5. Feature list

### Phase 1 — Ship-manager tender room (MVP)
- Vessel registry + docking-window planner (36-month logic, UWILD/EDD flags)
- Specification builder: canonical work-item library (seeded from §4.2/4.3 taxonomy), Excel import, copy-forward from previous docking, defect intake, versioning & spec freeze
- Yard directory: dock dimensions (length/beam/depth over blocks, cranes), physical-fit check vs vessel, region filter; curated seed data + self-serve edit
- Tender: invite yards, deadline, sealed-bid handling, clarification Q&A rounds with addenda broadcast
- Bid intake, two channels: (a) structured portal entry by the yard (free for yards — this seeds the two-sided network), (b) **AI ingestion** of PDF/Excel quotes → mapped lines + exclusions + confidence, human review UI
- Leveling matrix: canonical grid across yards; FX normalization; exclusions diff; benchmark deltas vs norms; unpriced-exposure panel
- TEC ranking with tunable weights; deviation cost auto-computed (routing service); side-by-side award memo generation (PDF)
- Negotiation round tracking (revised bids versioned, delta view)
- Award + contract checklist; tariff capture vault
- Exports throughout (Excel of the leveling matrix — meet superintendents where they are)

### Phase 2 — Execution & settlement
- VO log with tariff-priced VOs, approval workflow, dispute states, daily cost curve vs budget
- Final account reconciliation; growth analytics; yard scorecards; fleet docking-programme dashboard (KPIs: final/quoted growth %, overrun days, cost per docking day, spec-item VO origin analysis)

### Phase 3 — Yard workbench (seller side)
- Yard tender inbox; structured bid composer fed by the yard's own **tariff book** (uploadable; man-hour norms × labour rate × per-customer commercial factor)
- **Estimate engine:** spec lines auto-priced from tariff book; estimator adjusts variance factor per customer tier / slot pressure; margin view
- Dock slot board (docks × dates, hold/confirm), workload by trade
- Bid analytics: win/loss by customer, region, discount level

### Phase 4 — Network
- Yard profiles public to managers; availability signals; anonymized benchmark indices (e.g., regional per-m² blasting ranges); reputation from settled dockings

### AI features (cross-cutting)
1. Quote parsing & normalization (flagship — Claude with structured outputs against the canonical taxonomy; human-in-the-loop review; never silently auto-accept)
2. Spec drafting from defect lists/photos and previous-docking copy-forward
3. Bid sanity checker vs benchmark norms ("Yard B's steel at 92 mh/t is 55% below guide-norm band — verify scope")
4. VO-risk predictor from unpriced items + yard history
5. Clarification-question drafter from detected ambiguities/exclusions

## 6. Non-goals (v1)
No yard production planning/ERP, no crew management, no spares procurement (adjacent marketplaces exist), no class-society integrations (manual entry of survey dates), no payment processing.

## 7. Security & tenancy (existential for a bid platform)
Hard multi-tenancy; **sealed bids** (no manager sees a bid before deadline unless configured open; no yard ever sees another yard's bid); tariff books are yard-confidential (used for that yard's pricing only unless yard opts into anonymized benchmarks); full audit log on every tender action (award defensibility); role-based access (superintendent/manager/viewer; yard estimator/commercial head).

## 8. Success metrics
Buyer: leveling time (days → hours), TEC vs sticker delta surfaced per tender, final/quoted growth % trend, % tenders with tariff captured pre-award. Seller: bid turnaround time, structured-bid share, win-rate insight adoption. Platform: yards with live profiles, tenders/quarter, two-sided tenders share.

## 9. Expert-scrutiny checklist (terms the product must use correctly)
Docking plan & block arrangement, lay days vs dock days, wharfage, cranage, fire watch, gas-free certificate, staging, tail shaft survey, keyless/keyed propeller, rudder pintle clearances, sea chests & gratings, anodes, Sa 2.5 blasting standard, spot/sweep/full blast, thickness gauging, ESP, special vs intermediate survey, UWILD, EDD, conditions of contract, owner's items, yard's standard tariff, variance/commercial factor, variation order, final account, ROB, off-hire, deviation.

## 10. Source register (verified 3-0 unless noted)
[1] IACS Rec. 133; UK MGN 672(M); SOLAS I/10(a)(v) — 36-month bottom-inspection rule
[2] IACS Rec. 133 / IMO Res. A.1053(27)→A.1186(33) — UWILD basis
[3] IACS Rec. 133; MGN 672(M) — EDD scheme, eligibility, 90-month cycle
[4] Butler, *A Guide to Ship Repair Estimates in Man-hours* (Elsevier, 2nd ed. 2012) — tariff-book build-up
[5] Butler Table 3.1 — steel renewal norms & factors
[6] Butler — per-m² hull treatment convention; grit-removal invoice inflation
[7] Butler Table 2.2 — general-services tariff taxonomy
[8] Northlake Shipyard published tariff (live-fetched) — real unit-rate structure
[9] Butler pp. 3–4 — yard variance factor; "quotes vary tremendously"
[10] Butler p. 105 + Table 2.1 — tariff capture, conditions of contract, block-shifting norms
[11] MariApps smartPAL Drydock product documentation (vendor-attested)
[12] BASS press + trade press — BASSnet Docking capabilities & customers
[13] Gap synthesis — absence-of-evidence based (medium confidence); Procureship/ShipServ/Moscord/SSI/Idwal/Kaiko/Pinpoint not exhaustively verified either way — re-verify before public competitive claims
