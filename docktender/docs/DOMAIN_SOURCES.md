# DockTender — Domain Sources Register

Every domain number shown in the product is planning-grade and traceable to a labelled
source. This register is the index; each work item's `norm_basis` field points here.
**Nothing in the app is presented as a yard tariff or a market price** — the norms are
guide values used only to compute leveling deltas ("this bid is 48% below the guide
norm"), which is exactly how a docking superintendent reads them.

## Labour-hour norms — `guide: Butler, Guide to Ship Repair Estimates (2012)`

Don Butler's *Guide to Ship Repair Estimates* is the standard published reference for
ship-repair man-hour estimating. Anchors used (mid-band values seeded; bands and
modifiers stored in each item's `factors`):

| Work | Guide norm | Modifiers |
|---|---|---|
| Flat shell plate renewal | **230 mh/t** (200–250 band) | curvature ×1.2 single / ×1.3 double; location tank-top 1.0 / wing 1.15 / under-deck 1.25; consumables ≈ $220/t |
| Internal structural members | 285 mh/t (250–320) | — |
| Keel/side blocks arrangement | 5–20 mh/block | scales with DWT |
| Tail shaft withdraw + survey (keyless) | 380–550 mh | keyed adds ~15% |
| Sea/overboard valve overhaul | 16–45 mh/valve | by nominal bore (DN) |
| Boiler retube | 3.5 mh/tube | economizer 4.0 |
| Main engine unit overhaul | 120 mh/cyl | aux 40 mh/cyl |

## Money rates — `guide: composite of published yard tariffs 2019–2024`

Blended from publicly circulated repair-yard tariff schedules and market commentary
(2019–2024). Regional steel all-in bands (USD/t, in each item's `factors.all_in_usd_t`):

| Region | Steel all-in $/t |
|---|---|
| ISC / China | 2,400–3,400 |
| Med / Turkey | 3,200–4,600 |
| SE Asia | 3,500–5,000 |
| N. Europe | 6,000–9,000 |

General-services anchors: dockage Aframax ≈ $12–18k/day; crane 25 t $250–350/hr; fire
watch $180–260/shift; gas-free certificate $3–6k; shore power $0.20–0.30/kWh; staging
$14–22/m³. Hull: HP wash $1.5–2.5/m²; spot blast Sa 2.0 $9–14/m²; full blast Sa 2.5
$18–28/m²; paint per coat $3–6/m². Docking+undocking lump: MR ≈ $70–110k, Aframax/LR2
≈ $110–170k.

## Yard directory — `Planning-grade dock data`

Dock dimensions (length/beam/depth-over-blocks/max DWT) in `yards.json` are curated
approximate figures for physical-fit filtering and shortlisting only — not contractual
dock specifications. Compiled from public yard capability listings. Treat as a planning
aid, verify against the yard before commitment (same posture as PassagePilot's ports).

## Regulatory basis

- **36-month bottom inspection** — SOLAS I/10(a)(v) and classification-society rules
  require two bottom inspections in dry-dock within any five-year period, with the
  interval between them not exceeding 36 months. This is the hard stop the docking
  clock computes.
- **UWILD** — In-water survey may satisfy an intermediate bottom inspection for eligible
  vessels (class-approved), deferring a dry-docking; when unavailable it drives the
  window ("IS + UWILD lapse").
- **EDD** — Extended Dry-Docking schemes (IACS Rec. 133) can extend intervals for
  qualifying vessels; surfaced as an informational flag only, never auto-applied.

## Discipline

Adding any new number to the product requires a new row here with its source label.
The seed builders assert every work item has a non-empty `norm_basis`; CI enforces it.
