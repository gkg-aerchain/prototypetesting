# DockTender — Execution Plan

v1.0 · July 2026 · This document is the **single source of truth for the build**.
It was produced with high-effort reasoning so the executing session does not have to
re-derive anything: every decision below is **locked** — execute, don't relitigate.
Companions: `PRD.md` (why), `BUILD_PLAN.md` (original phasing), `../design/design_direction.html`
(the approved visual direction, v6), `../design/tokens.css` (extracted tokens).

---

## 0. Locked decisions (do not reopen)

| Topic | Decision |
|---|---|
| Product scope | Ship-manager (buyer) side first. Yard workbench is Phase 3 — out of scope for now. |
| Repo / branch | Build in `gkg-aerchain/prototypetesting`, branch `claude/marine-app-repo-ljpekw`, under `docktender/`. If the user later creates a `dock-tender` repo and asks to move it, copy the tree — do not rewrite. |
| Design | v6 "Signal & Waterline": dark navy bridge chrome (`#0B1826`) rail/masthead over a light working deck; dual light/dark themes; **signal accent is a per-user setting** with 5 options (cerise default, marigold, verdigris, azure, violet). Full tokens in §2. |
| Signature element | The Waterline fleet timeline (spec in §7.2). Build it pixel-faithful to the mock. |
| Typography | Geist (400/500/600) + Geist Mono (400/500), inlined as woff2 data-URI CSS at `design/fonts/geist_inline.css`. No other faces. |
| Stack | Next.js 14 + TypeScript + Tailwind (frontend); FastAPI + Python 3.11 + SQLAlchemy (backend); pytest; Docker compose; GitHub Actions CI. |
| Database | SQLAlchemy models written Postgres-ready (UUID pk as strings, JSON columns, indexed FKs), but the demo runs SQLite exactly like PassagePilot: `DATABASE_URL` env, Vercel fallback `sqlite:////tmp/docktender.db`, boot-time demo seeding when `DEMO_SEED=1` (default) and URL starts with `sqlite`. Production Postgres/RLS is documented, not built now. |
| AI | Anthropic API, model `claude-opus-4-8`, structured outputs (tool with strict JSON schema), manual tool loop — same pattern as PassagePilot's assistant. AI never auto-commits: everything lands in a review queue. |
| Demo tenant | "Galene Maritime", superintendent S. Nair. Demo login seeded at boot: `superintendent@docktender.demo` / `DryDock2026!` (admin). |
| Demo scenario | Tender `TND-2026-014`, M/T Kalymnos Voyager SS No. 2, 3 bids: Drydocks World Dubai (complete, TEC winner $2.90M), Sembcorp Admiralty (fast but 1,890 nm deviation, $3.04M), Besiktas (lowest sticker $2.19M, highest TEC $3.15M). Numbers in §4.4 — the UI must reproduce the approved mock exactly. |
| Deploy | Vercel, two projects: `docktender` (frontend) + `docktender-api` (Python serverless ASGI, `api/index.py`, rewrite all→`/api/index`, maxDuration 300). Same `vdeploy.py` REST flow as PassagePilot. User sets `ANTHROPIC_API_KEY` in the dashboard themselves. Always give the user clickable URLs. |

Non-negotiable quality bar (user's words): *"extremely thorough and detailed, without any
dead ends or just shell items… a completely working solution with a beautifully designed
front end… the perfect blend of simplicity and perfection."* Every nav item routes to a
fully working screen. No "coming soon". Every domain number is traceable (§12).

---

## 1. Repo layout (exact)

```
docktender/
  README.md                     # what it is, how to run, demo creds, deploy
  docker-compose.yml            # frontend + backend dev
  .github/workflows/ci.yml     # pytest + next build (workflow may live at repo root — see note)
  docs/
    EXECUTION_PLAN.md           # this file
    PRD.md  BUILD_PLAN.md
    ARCHITECTURE.md             # written during Phase 0 from this plan
    API.md                      # endpoint contract, kept in sync
    DOMAIN_SOURCES.md           # register: every norm/tariff guide value + source label
  design/
    design_direction.html       # approved v6 artifact source
    tokens.css                  # canonical tokens (both themes, 5 accents)
    fonts/geist_inline.css
  backend/
    requirements.txt  vercel.json  api/index.py
    app/
      main.py                   # FastAPI app, lifespan: create tables + demo seed
      core/config.py            # env, /tmp sqlite fallback, anthropic model
      core/security.py          # bcrypt direct (72-byte truncate!), JWT
      db.py  models.py  schemas.py
      seed/
        work_items.json         # canonical library (§4.1)
        yards.json              # yard directory (§4.2)
        demo.py                 # fleet/tender/bids fixtures (§4.3–4.4)
      engines/
        clock.py                # docking-window / 36-month rule (§5.1)
        normalization.py        # canonical mapping, units, FX (§5.2)
        norms.py                # guide-norm lookups + deviation flags (§5.3)
        tec.py                  # total evaluated cost (§5.4)
        exposure.py             # VO-risk model (§5.5)
        awards.py               # award memo PDF (reportlab)
      ai/
        client.py               # anthropic client + tool loop
        bid_parser.py           # PDF/xlsx/text → bid_lines (§8.1)
        sanity.py  clarifier.py # (§8.2, §8.3)
        assistant.py            # chat endpoint tools (§8.4)
      routers/
        auth.py fleet.py programme.py specs.py workitems.py
        yards.py tenders.py bids.py leveling.py awards.py
        executions.py settlements.py ai.py health.py
    tests/
      test_auth.py test_clock.py test_normalization.py test_tec.py
      test_exposure.py test_api_flow.py test_parser_golden.py
      golden/quote_01.txt … quote_10.txt   # synthetic yard quotes (§9)
  frontend/
    package.json  next.config.js  tailwind.config.ts
    src/
      app/ (routes in §7)  components/  lib/api.ts  lib/format.ts
      styles/globals.css    # imports tokens.css + fonts
```

CI note: GitHub Actions only reads workflows from the repo root `.github/`. Place the
workflow at the **repo root** (`/.github/workflows/docktender-ci.yml`) with
`paths: ['docktender/**']` filters, `working-directory: docktender/...` steps.

---

## 2. Design tokens (canonical — copy verbatim into tokens.css / Tailwind)

Two themes (light default per OS, user-toggleable) × five accent options. The accent
is **one token set**; components must only ever reference `--signal`, `--signal-deep`,
`--signal-tint` — never a hex.

### 2.1 Light theme (working deck)
```css
--chrome:#0B1826; --chrome-2:#122236; --chrome-ink:#E9EEF3; --chrome-dim:#8DA0B3;
--paper:#F4F6F7; --card:#FFFFFF; --well:#EBEEF0;
--ink:#14202C; --ink-2:#4E5D6B; --ink-3:#8B99A6;
--hairline:#E4E8EB; --hairline-2:#D3DAE0;
--good:#2C7A57; --good-tint:#E3F0E9;  --warn:#A96F00; --warn-tint:#F6EDD5;
--crit:#BF3B36; --crit-tint:#F8E7E6;
--steel:#64809A; --sea:#DCE6EC;                 /* waterline neutrals */
--s1:#0084A0; --s2:#4A5FA5; --s3:#B07A2A; --s4:#9C4C93;  /* categorical, CVD-validated */
--note:#8A6A00;
```

### 2.2 Dark theme
```css
--chrome:#0A141F; --chrome-2:#0F1D2D; --chrome-ink:#E9EEF3; --chrome-dim:#7E93A7;
--paper:#0E161E; --card:#131D27; --well:#1A2631;
--ink:#E7ECF0; --ink-2:#A6B4C0; --ink-3:#67778A;
--hairline:#22303C; --hairline-2:#2E3E4C;
--good:#58B389; --good-tint:#10281D;  --warn:#D3A140; --warn-tint:#2C220D;
--crit:#E0736D; --crit-tint:#331513;
--steel:#587795; --sea:#142433;
--s1:#31A0BC; --s2:#6D83DC; --s3:#C1802A; --s4:#B5679F;
--note:#CBA83E;
```

### 2.3 Signal accent options (user setting, persisted per user; default `cerise`)
| key | light `--signal` / `-deep` / `-tint` | dark `--signal` / `-deep` / `-tint` | companion shift |
|---|---|---|---|
| cerise (default) | `#D62A6E` `#AD1257` `#FAE3EE` | `#EE6FA4` `#D62A6E` `#3A1226` | — |
| marigold | `#B8860B` `#7E5C00` `#F7ECD2` | `#D9A62E` `#7E5C00` `#33270A` | while active: light `--warn:#8F4E1D --warn-tint:#F5E7DA`; dark `--warn:#C88A4A --warn-tint:#2F1D0E` |
| verdigris | `#0F8C7D` `#0A6A5E` `#DFF1EE` | `#3DBFAE` `#0A6A5E` `#0E2A26` | — |
| azure | `#2E6BE6` `#1E4FD0` `#E4EBFC` | `#7AA5FF` `#1E4FD0` `#182448` | — |
| violet | `#6D4AE7` `#5433C4` `#EAE4FB` | `#9B85F2` `#5433C4` `#221743` | — |

All values are contrast-verified (mark ≥3:1 on paper, text ≥4.5:1, white-on-fill ≥4.5:1
— except marigold/verdigris dark fills, where buttons use `--signal-deep` bg which passes).
Button hover = `filter: brightness(1.12)`, never a lighter fill swap.
Implementation: `data-accent` attribute on `<html>`, stored in user profile (backend
`users.accent` column) and mirrored to localStorage; Settings screen hosts the picker.

### 2.4 Accent discipline (enforced in review)
The signal appears ONLY as: the today-line, a closing window ≤180 days, the single
primary action per screen, and the recommendation (winner card crown + rank label).
Semantic good/warn/crit never decorate. Categorical s1–s4 appear only in cost-composition
bars and their legends.

### 2.5 Type scale
Hero figures (the one number a screen): Geist Mono 42–52px. TEC card figures: mono 34px.
Stat values: mono 25px. h1 21px/600, panel titles 14px/600, body 15px, table 13px,
mono microlabels 10.5–11px uppercase +0.09–0.14em tracking. `tabular-nums` on all figures.

---

## 3. Data model (SQLAlchemy — exact tables)

String UUID pks (`id = Column(String, primary_key=True, default=lambda: uuid4().hex)`).
`created_at/updated_at` on all. FKs indexed. `org_id` on every tenant-scoped table and
**every query filters by it** (this is the RLS stand-in — write a helper dependency).

```
organizations   id, name, kind ENUM(manager|yard)
users           id, org_id, email UNIQUE, password_hash, full_name, role ENUM(admin|superintendent|viewer),
                accent DEFAULT 'cerise', theme DEFAULT 'system'
vessels         id, org_id, name, vessel_type, dwt, loa_m, beam_m, summer_draft_m, gt,
                built_year, class_society, last_docking_date, last_docking_yard,
                special_survey_no, uwild_ok BOOL, edd_enrolled BOOL, tce_usd_day,
                notes; computed props via engines/clock.py (NOT stored: window dates)
yards           id, name, country, region ENUM(SEA|MEast|ISC|FarEast|Med|NEur|Am),
                labor_rate_band ENUM(low|mid|high), lat, lon, notes
docks           id, yard_id, name, kind ENUM(graving|floating), length_m, beam_m,
                depth_over_blocks_m, max_dwt, cranes_json
work_items      id, code UNIQUE (e.g. "GS-001"), section INT 1..10, section_name,
                title, uom, norm_value, norm_unit, norm_basis (label, e.g.
                "guide: Butler 2012 T3.1"), factors_json, typical BOOL
specifications  id, org_id, vessel_id, title, docking_window_start/end,
                status ENUM(draft|frozen), version INT, frozen_at
spec_items      id, spec_id, work_item_id NULLABLE, line_no, title, qty, uom,
                qty_tbc BOOL, origin ENUM(class|defect|owner|previous), notes
tenders         id, org_id, spec_id, ref UNIQUE (TND-YYYY-NNN), status
                ENUM(draft|issued|closed|awarded), deadline, fx_date, fx_rates_json,
                offhire_usd_day, sealed BOOL DEFAULT true
invitations     id, tender_id, yard_id, status ENUM(invited|declined|bid_received)
clarifications  id, tender_id, question, asked_by, answer, addendum_no, published BOOL
bids            id, tender_id, yard_id, revision INT, currency, validity_date,
                dock_id NULLABLE, dock_days, slot_start/end, terms_json,
                tariff_captured BOOL, sealed_until, source ENUM(portal|ai_ingest)
bid_lines       id, bid_id, spec_item_id NULLABLE, raw_text, uom, qty, rate, amount,
                state ENUM(priced|included|excluded|unpriced), assumptions,
                ai_confidence FLOAT NULLABLE, reviewed_by NULLABLE, reviewed_at
tariffs         id, yard_id, bid_id NULLABLE, doc_name, lines_json  # captured pre-award
evaluations     id, tender_id, params_json (fx_date, offhire, growth_default, fuel_usd_t,
                speed_kn), computed_at
tec_components  id, evaluation_id, bid_id, normalized_usd, deviation_usd, offhire_usd,
                vo_exposure_usd, deviation_nm, deviation_days, flags_json, rank INT,
                recommended BOOL
awards          id, tender_id, bid_id, memo_note, checklist_json, awarded_at
variation_orders id, org_id, award_id, vo_no, title, spec_item_id NULLABLE, qty, uom,
                proposed_usd, tariff_line_ref NULLABLE, tariff_usd NULLABLE,
                state ENUM(proposed|approved|disputed|rejected), decided_by, decided_at
final_accounts  id, award_id, lines_json, quoted_usd, final_usd, growth_pct, closed_at
yard_scores     id, yard_id, docking_ref, growth_pct, overrun_days, quality INT 1..5,
                hse INT 1..5, notes
audit_log       id, org_id, actor_id, action, entity, entity_id, detail_json, ts
agent_events    id, org_id, agent ENUM(bid_parser|sanity_checker|docking_clock|
                vo_reconciler|clarifier), severity ENUM(info|warn|crit), vessel_id NULL,
                message, evidence, needs_decision BOOL, decided_by NULL, ts
```

Every mutation to `specifications/tenders/bids/awards/variation_orders` appends an
`audit_log` row (helper `audit(db, org, actor, action, entity)` — call it in routers).

---

## 4. Seed data (Phase 0 critical path)

### 4.1 `work_items.json` — canonical library, ~180 items, 10 sections
Sections and target counts (codes `XX-NNN`):
1. **GS** General Services (24): dockage/day, wharfage/day alongside, docking+undocking
   operation, keel/side blocks arrangement, fire watch/shift, gas-free inspection & cert,
   shore power/kWh, cooling water, fresh water/t, garbage/skip, sludge disposal/m³,
   crane 25t/hr & 60t/hr, forklift/hr, staging/m³ erect+dismantle, transport in yard,
   ballast handling, tank ventilation/day, watchman, environmental levy, hot-work permit,
   riding-crew berths/day, agency & security.
2. **HT** Hull Treatment & Painting (22): HP fresh-water wash/m², spot blast Sa2.0/m²,
   full blast Sa2.5/m², sweep blast/m², power tool St3/m², anodes supply+fit/ea by kg,
   paint application per coat/m² (AC, AF, boot-top, topside), deck non-skid, draft marks,
   plimsoll re-mark, hold coating (bulkers).
3. **ST** Steel Renewals (18): shell plate ≤12.5/15/20 mm per t; internals (frames,
   brackets, stiffeners) per t; deck plate per t; wing-tank internals per t (location
   factor); double-bottom per t; pipe tunnel; insert plates ≤0.25 m²/ea; doubler
   (temporary) /ea; NDT spot UT/point; class witness/attendance per visit.
4. **SV** Sea Valves & Overboards (10): overhaul gate/globe/butterfly DN80–DN400 /ea;
   sea chest clean+coat /ea; grids /ea; chest anodes; pressure test /ea.
5. **PR** Propulsion & Tail Shaft (16): tail shaft withdraw+survey (keyless), seal
   overhaul (fwd/aft), propeller polish grade A–C, propeller removal/refit, pitch check,
   rope guard, stern tube oil analysis, rudder clearances, pintle survey, bow thruster
   overhaul.
6. **BE** Boiler & Economizer (10): retube per tube, casing steel per t, refractory /m²,
   safety-valve overhaul+float /ea, burner overhaul, hydrotest.
7. **PI** Piping & Tanks (20): pipe renewal per inch-meter (steel/cunifer), tank clean
   for hot work per m³ (slop/cargo/bunker grades), cargo tank steam, IGS deck seal,
   valves per DN, hydraulic lines, air & sounding pipes/ea.
8. **MC** Machinery Overhauls (22): ME unit overhaul per cyl, aux engine per cyl,
   cooler tube-stack retube/clean /ea, pumps (centrifugal/screw) /ea, purifier, air
   compressor, windlass, mooring winch, crane wire renewal per m, chain calibration.
9. **EL** Electrical & Automation (14): motor overhaul by kW band, MSB maintenance,
   megger survey, alarm point test /point, ICCP anodes, battery bank renewal,
   navigation-light panel, EGCS/BWTS sensor service.
10. **CS** Class & Surveys / Owner's items (12): SS hull survey attendance, tail-shaft
    survey attendance, UWILD in lieu (note), load-line, MLC inspection, anchors & chain
    ranging+EGD per shackle, liferaft service /ea, gangway load test, misc owner works.

Each item: `{code, section, section_name, title, uom, norm_value, norm_unit,
norm_basis, factors, typical}` where `norm_basis` **always** carries a source label,
e.g. `"guide: Butler, Guide to Ship Repair Estimates (2012), steel tables"` or
`"guide: composite of published yard tariffs 2019–2024"`. Guide norm anchors
(planning-grade, labeled as such — NOT invented precision):
- Steel: flat shell plate **230 mh/t** (200–250 band); curvature ×1.2 single / ×1.3
  double; location factors tank-top 1.0, wing tank 1.15, under-deck 1.25; consumables
  ≈ $220/t; typical all-in rate bands: ISC/China $2.4–3.4k/t, Med/Turkey $3.2–4.6k/t,
  SEA $3.5–5k/t, N.Europe $6–9k/t.
- Hull: wash $1.5–2.5/m², spot Sa2.0 $9–14/m², full Sa2.5 $18–28/m², paint per coat
  $3–6/m².
- GS anchors: dockage Aframax ≈ $12–18k/day; crane 25t $250–350/hr; fire watch
  $180–260/shift; gas-free cert $3–6k; shore power $0.20–0.30/kWh; staging $14–22/m³.
- Keel blocks: 5–20 mh/block scaling with DWT; docking+undocking lump: MR ≈ $70–110k,
  Aframax/LR2 ≈ $110–170k.
- PR: keyless tail shaft withdraw+survey 380–550 mh; sea valve overhaul 25–45 mh/valve.
Populate every item with a mid-band value + `factors` for the modifiers. ~180 rows is
the target; do not pad with duplicates.

### 4.2 `yards.json` — ~45 yards, planning-grade dock data
Include at least: Seatrium Admiralty + Tuas (SG), PaxOcean (SG), Drydocks World Dubai,
ASRY (Bahrain), Oman Drydock Duqm, N-KOM (Qatar), Colombo Dockyard, Cochin Shipyard,
Hindustan Shipyard Visakhapatnam, Chattogram DD, COSCO Zhoushan / Dalian / Shanghai /
Guangdong, Yiu Lian Shekou, HRDD (Shanghai), CUD Weihai, Besiktas, Gemak, Desan,
Sedef (Tuzla), Gibdock, Astander, Astican, Navantia Cádiz, Palumbo Malta, Skaramangas,
Remontowa, Fayard, Damen Brest / Dunkerque / Verolme, Blohm+Voss, Lloyd Werft,
Grand Bahama, Detyens, Vigor Portland, Seaspan Victoria, Astilleros Talcahuano,
Dormac Durban, EBH? (choose 45 real, well-known repair yards). Per yard: 1–3 docks with
`length_m/beam_m/depth_over_blocks_m/max_dwt/kind`, region, labor band, lat/lon.
Values are **planning-grade** (README + `DOMAIN_SOURCES.md` must say so, exactly like
PassagePilot's ports.json disclaimer).

### 4.3 Demo fleet — Galene Maritime, 12 vessels (Greek-island names)
The five from the mock (exact statuses) + seven fillers:
| Vessel | Type/DWT | Driver | State (as of Thu 3 Jul 2026) |
|---|---|---|---|
| Kalymnos Voyager | LR2 115,000 | SS No. 2 | window closes **14 Nov 26 (134 d)**, 3/4 bids in, leveling ready |
| Thera Compass | Aframax 105,000 | IS + UWILD lapse | closes 02 Mar 27 (242 d), tender out, 7 invited |
| Naxos Meridian | MR 49,900 | SS No. 4 | closes 19 Jun 27 (351 d), spec 40% drafted |
| Paros Horizon | LR2 114,500 | SS No. 1 | **in dock day 6/13**, 2 VOs open |
| Milos Beacon | MR 49,900 | SS No. 3 | completed 12 Jun, final account open |
| + Sifnos Trader, Serifos Wind, Amorgos Spirit, Folegandros Bay, Ikaria Dawn, Skyros Light, Andros Pioneer | MR/Aframax mix | — | windows 2027–28, planning |
TCE for off-hire: LR2 $22,000/day, Aframax $19,500/day, MR $16,000/day.

### 4.4 Demo tender TND-2026-014 (must reproduce the approved mock numbers)
312 spec lines (generate: full §1–§6 + selected §7–§10 items with plausible qty),
FX frozen 01 Jul 26, off-hire $22,000/day. Key section totals per bid:

| Section | Drydocks Dubai | Sembcorp | Besiktas |
|---|---|---|---|
| §1 General services | **$318,400** (best) | $342,100 | $296,750 + excl. grit disposal |
| §2 Hull 12,400 m² | $486,200 | **$471,900** (best) | $438,300 (−9% low band) |
| §3 Steel 48.2 t TBC | **$561,500** (best) | $602,800 | $402,100 (104 mh/t, −48% vs 230 norm) |
| §4 Sea valves ×14 | $128,900 | **$119,400** (best) | $131,200 |
| §5 Tail shaft | **$96,300** (best) | $104,750 | $92,000 + excl. class fees |
| §6 Boiler retube 42 | **$214,600** (best) | — unpriced | $198,400 |

Bids: Dubai `$2.41M`, 13 dock days, slot 28 Oct–10 Nov, Dock 2 (366 m), tariff annexed,
0 exclusions → TEC **$2.90M** = 2.41 + 0.09 deviation (420 nm) + 0.29 off-hire + 0.12 VO.
Sembcorp `$2.52M`, 12 days, Dock 4 (384 m), boiler unpriced → TEC **$3.04M** = 2.52 +
0.16 (1,890 nm, $162k steaming noted) + 0.26 + 0.09. Besiktas `$2.19M`, 16 days, floating
dock 290 m, 6 exclusions, no tariff → TEC **$3.15M** = 2.19 + 0.22 + 0.35 + 0.39
($387k modelled exposure). Calibrate `engines/tec.py` inputs (fuel $580/t VLSFO, 12.5 kn
ballast deviation speed) so the engine **computes** these to ±$0.01M rather than
hard-coding. Besiktas bid also carries 4 low-confidence AI lines (queue item), agent
feed events exactly as in the mock (Bid Parser 82 lines/6 exclusions; Sanity Checker
104 vs 230 mh/t; Docking Clock Naxos 89 d; VO Reconciler VO-06 $11,840 tariff match).
Paros Horizon execution: 7 VOs total, 2 open (VO-07 sea valve seat $4,100 over tariff).
Milos Beacon final account: quoted $1.84M, final $2.01M, growth +9.4% (drives the
"Final vs quoted +9.4%, ▼2.1 pts" stat).

---

## 5. Engines (pure functions, fully unit-tested)

### 5.1 `clock.py`
`docking_window(vessel, today)` → `{window_start, window_end (hard stop), days_left,
driver}`. Rules: hard stop = `last_docking_date + 36 months` (SOLAS I/10(a)(v) /
class 36-month bottom-inspection rule); intermediate survey inspections may be UWILD if
`uwild_ok` (flag as `driver="IS + UWILD lapse"` when not); `edd_enrolled` extends per
IACS Rec 133 note (informational flag only). `window_start = hard_stop − 120 days`
(planning convention, documented). Emit `severity`: signal ≤180 d, steel otherwise.

### 5.2 `normalization.py`
- `to_base(amount, ccy, fx_rates)` — frozen-FX conversion (rates stored on tender).
- `unit_convert(qty, from_uom, to_uom)` — m²/ft², t/kg, per-piece passthrough; raise on
  unknown pairs (surface in review UI, never guess silently).
- `level_bid(bid, spec)` → per spec_item: matched line(s), state
  (priced/included/excluded/unpriced), normalized USD. Matching precedence:
  `spec_item_id` (portal bids) → exact `work_item.code` in raw_text → AI-proposed
  mapping (must be human-accepted before it counts, `reviewed_by` set).
- `exclusions_diff(bids)` → the "excluded/unpriced by yard" panel data.

### 5.3 `norms.py`
`check_line(line, work_item, qty_basis)` → flags. Rules: rate/mh below **0.60×norm** →
`warn "−NN% vs guide norm"` (the Besiktas steel case: 104 vs 230 mh/t = −55%… mock says
−48%, which is vs the 200 low band — use the low band for the % and say so in the flag
detail); above 1.8×norm → `warn "above norm band"`; `qty_tbc` + below-norm rate →
`crit "VO growth pattern"`. Every flag carries `norm_basis` for the evidence line.

### 5.4 `tec.py`
```
TEC = N + D + O + V
N = Σ normalized priced lines (USD, frozen FX)
D (deviation) = extra_nm/(speed_kn*24) days * fuel_t_day * fuel_usd_t + port_fees_lump
    extra_nm = 2 * (gc_distance(discharge_port, yard) * 1.15 routing factor)  — or the
    PassagePilot routing API when ROUTING_API_URL is configured (optional env)
O (off-hire) = (dock_days + deviation_days) * offhire_usd_day
V (VO exposure) = Σ(unpriced+excluded items priced at tariff median for the region)
    + growth_factor * N   where growth_factor = yard_scores.mean(growth_pct) if ≥1
    docking history else evaluation.params.growth_default (default 0.094)
```
Output `tec_components` rows + `rank` + `recommended` (lowest TEC with zero `crit`
flags; if the lowest carries crit flags, recommend next and emit an explanation flag —
the design's "never argues both sides" rule needs one clear answer).

### 5.5 `exposure.py`
`vo_exposure(bid, spec, tariffs, region_medians)` → itemized exposure lines (the
"Open exposure model" panel): each unpriced/excluded item, the tariff/median used,
and the modelled USD. Total must reconcile with `tec.py`'s V to the cent.

---

## 6. API surface (FastAPI, `/api` prefix, JWT bearer; public = *)

```
*GET  /api/health                          {status, seeded, version}
*POST /api/auth/register|login             → {access_token}; GET /api/auth/me
PATCH /api/me                              {accent?, theme?, full_name?}
GET   /api/programme                       command-center payload (§7.1): waterline[],
                                           focus{}, stats[], fleet_clock[], queue[], feed[]
GET   /api/fleet ; POST/GET/PATCH/DELETE /api/vessels[/{id}]
GET   /api/work-items?section=&q=
GET   /api/yards?vessel_id=                physical-fit filter: any dock length≥LOA+6m,
                                           beam≥beam+2m, depth_over_blocks≥draft (flag margins)
POST  /api/specs {vessel_id,title}; GET /api/specs[/{id}]
POST  /api/specs/{id}/items (single|bulk from library|xlsx import); PATCH/DELETE item
POST  /api/specs/{id}/freeze               versions + locks
POST  /api/tenders {spec_id,deadline,offhire,fx}; GET /api/tenders[/{id}]
POST  /api/tenders/{id}/invite {yard_ids}; POST .../clarifications ; POST .../addenda
POST  /api/tenders/{id}/bids               structured portal bid (yard persona not built;
                                           used by demo seed + manual entry form)
POST  /api/tenders/{id}/bids/ingest        file/text → ai/bid_parser → draft bid+lines
GET   /api/bids/{id}/review                lines + confidence + proposed mappings
PATCH /api/bids/{id}/lines/{line_id}       accept/remap/exclude (stamps reviewed_by)
GET   /api/tenders/{id}/leveling           TEC cards + matrix + exclusions panel (§4.4 shape)
POST  /api/tenders/{id}/evaluate           params → recompute evaluation
GET   /api/tenders/{id}/exposure           §5.5 itemized model
POST  /api/tenders/{id}/award {bid_id,note}; GET /api/awards/{id}/memo.pdf
GET   /api/executions ; GET /api/executions/{award_id}
POST  /api/executions/{id}/vos ; PATCH /api/vos/{id} {state,decided reason}
GET   /api/settlements ; POST /api/settlements/{award_id}/close {final lines}
GET   /api/agents/events?needs_decision= ; PATCH /api/agents/events/{id} (decide)
POST  /api/ai/chat                         assistant (503 if no key — same as PassagePilot)
```
`GET /api/programme` is the performance-critical aggregate — one handler, ≤6 queries.

---

## 7. Frontend (Next.js App Router; screens map 1:1 to the approved mock)

Shell: fixed dark rail (`--chrome`) 212px — brand "Dock**Tender**" (Tender in signal),
nav Programme/Specifications/Tenders/Yards/Executions/Settlements + Settings gear at
foot with org/user line; stage on `--paper`. Rail active item: signal left-edge 2px on
`--chrome-2`. Auth pages centered card on chrome ground. Theme + accent both live on
`<html data-theme data-accent>`, hydrated from `/api/auth/me`, mirrored to localStorage
(pre-hydration inline script prevents flash).

### 7.1 `/programme` — Command center (the money screen #1)
Exact composition from the mock, top to bottom: header (date line + "Start a
specification" primary); **Waterline panel**; focus strip `1.7fr 1fr 1fr 1fr` — hero
"next hard stop" card (signal left edge, k-label in signal, 42px mono countdown, sub
line, "Open leveling →"), Programme $M, Tenders in flight, Final vs quoted; then
`1fr 330px`: Fleet docking clock table (vessel/driver/window closes/status pill,
row-links) beside "Needs your decision" queue (agent_events needs_decision) + "Agent
activity" feed (severity dot, agent name, age, message, mono evidence line).

### 7.2 `<Waterline/>` — the signature component (data-driven SVG)
Props: `{vessels: [{name, sub, x_window:[start,end] dates, status:
closing|window|planning|in_dock, closes_label}], today, horizon_months=18}`.
Geometry (from the approved mock, viewBox `0 0 1040 176`): month grid x = 30 + i·(980/17)
with mono labels y=136 (label every 2nd month, year suffix on Jan/first); waterline at
y=92 (`--steel` 1.5px over `--sea` rect 92→120); window bands rounded rects y=86 h=12 —
`--signal` fill when status=closing, `--steel` at opacity 1/.65/.45 by proximity;
vessels above: name 600 y=42, mono status sub y=56 (signal-deep when closing), stem
x=window-midpoint y 60→84 with 3.2px dot on the band; in-dock: `--chrome` chip below the
line (y=100 h=16, white 10px label "Name · D6/13"); today: 2px signal rule y 18→122 +
mono "TODAY". Hover: raise a card (name, driver, window, CTA); click → vessel docking
file. Also render a `<caption>`-equivalent table (sr-only + toggle) for accessibility.

### 7.3 `/specifications` + `/specifications/[id]`
List (status, vessel, window, % complete) → builder: left = section tree (§1–§10 with
line counts), center = line table (code, title, qty+uom, TBC toggle, origin chip,
notes), right = library drawer (search work_items, click-to-add, shows norm + basis).
Toolbar: import Excel (maps columns → items, unmatched to review), copy-forward from
vessel's previous spec, **Freeze** (versions, locks editing, enables tender creation).
No dead ends: import + copy-forward must work against demo data.

### 7.4 `/tenders` + `/tenders/[id]` (room) + `/tenders/[id]/leveling`
Room tabs: Overview (deadline countdown, invited yards with fit-check chips, bid
status), Q&A (clarifications → publish as addendum), Bids (received list → review
screen: line grid with `ai_confidence` heat, accept/remap per line, bulk-accept ≥0.9,
"4 low-confidence lines" banner drives the queue item). Leveling = the approved mock:
TEC legend (s1–s4), 3 cards (winner: signal crown bar + "RANK 1 · RECOMMENDED",
34px TEC, sticker caption, composition tecbar with 2px gaps, flag chips, verdict
note), matrix by section (best cell = good inset edge + tint, flags inline,
"— unpriced · TBA" crit), footer note + "Open exposure model" → drawer with §5.5
itemization. "Draft award memo" (signal button) → award flow: memo preview (vessel,
tender ref, ranking table, recommendation rationale auto-drafted from flags),
contract checklist (tariff annexed? validity? dock confirmed? terms?), confirm →
PDF via `awards.py`, tender → awarded, tariff → vault.

### 7.5 `/yards`
Directory with region filter + "fits vessel" selector (runs the §6 fit rule, shows
margin chips e.g. "L +14 m · B +3.2 m · depth +1.1 m"); yard page: docks table,
history (yard_scores), captured tariffs list.

### 7.6 `/executions` + `/settlements`
Executions: live dockings (Paros Horizon day 6/13 progress bar), VO log table (no,
title, qty, proposed vs tariff — over-tariff delta in crit, state chips), approve/
dispute actions (stamp audit). Cost curve: quoted → +approved VOs running total
(simple SVG line, tokens only). Settlements: final account per docking (lines, quoted
vs final, growth %), close action; fleet KPI strip (avg growth %, avg overrun days,
by-yard scorecard table — drives yard_scores).

### 7.7 `/settings`
Profile; **theme** (System/Light/Dark) and **signal picker** — 5 swatch cards exactly
like the direction page (uses the same tokens; persists via `PATCH /api/me`, applies
instantly, marigold shifts warn to umber). Org users list (admin).

### 7.8 Assistant
Docked panel (rail foot button) → chat over `POST /api/ai/chat`; context: current
route entity ids. Tools (§8.4). Renders evidence lines in mono like the feed.

---

## 8. AI integration (all `claude-opus-4-8`, structured outputs, human-in-the-loop)

### 8.1 Bid Parser — `POST /bids/ingest`
Input: pasted text / uploaded PDF (pypdf extract) / xlsx (openpyxl). Chunk ≥30k chars.
Tool schema `emit_bid` (strict): `{currency, validity_date?, dock_days?, slot?,
exclusions_text?, lines: [{raw_text, uom?, qty?, rate?, amount?, state, proposed_code?,
confidence 0..1, assumptions?}]}`. Post-process: map `proposed_code`→work_item, attach
to spec via §5.2 precedence, create draft bid `source=ai_ingest`, lines with
`confidence<0.75` flagged; emit agent_event (Bid Parser, "N lines mapped, M exclusions
detected", evidence `BID-xxxx · K/N high confidence`, needs_decision if any low).
**Never** auto-accept: leveling only counts `reviewed_by IS NOT NULL` lines or portal
lines.

### 8.2 Sanity Checker — post-review hook per bid
Runs `norms.py` over accepted lines; each finding → agent_event with evidence
`"Norm 230 mh/t · guide: Butler T3.1"`. Pure-engine (no LLM call) — the "AI" here is
the norms table; label the agent honestly in docs.

### 8.3 Clarifier — button in Q&A tab
LLM drafts clarification questions from exclusions_diff + low-confidence assumptions;
tool `emit_questions {questions:[{to_yard, question, reason}]}`; lands as drafts
(needs_decision event "3 clarification questions drafted"), superintendent edits/sends.

### 8.4 Assistant tools
`get_programme()`, `get_tender(ref)`, `get_leveling(ref)`, `get_vessel(name)`,
`get_norm(code)` — read-only, org-scoped. System prompt: docking-superintendent
domain persona; cite evidence (norm basis, tender ref) in answers; never reveal a
sealed bid before deadline (check `sealed_until`).
Golden eval: `tests/golden/quote_01..10.txt` — 10 synthetic yard quotes in varied
formats (lump-sum Turkish style w/ exclusions, per-line Singapore style, Chinese
tariff-ref style, messy email, two-currency, etc.) with expected-extraction JSON;
`test_parser_golden.py` asserts ≥90% line recall / ≥95% amount accuracy on high-
confidence lines. **Skip (pytest.mark.skipif) when no ANTHROPIC_API_KEY** — CI stays
green without secrets.

---

## 9. Tests (pytest, TestClient with lifespan; SQLite tmp file; DEMO_SEED=0 in tests)

- `test_clock.py`: 36-month math incl. leap/window edges; UWILD lapse driver; severity.
- `test_normalization.py`: FX freeze, unit conversions (incl. unknown-pair raise),
  matching precedence, unreviewed-AI-lines-don't-count.
- `test_tec.py`: **the demo calibration** — Dubai 2.90 / Sembcorp 3.04 / Besiktas 3.15
  (±0.01), ranks, recommended=Dubai, deviation nm/days, growth fallback.
- `test_exposure.py`: itemized total == TEC V; region medians; tariff precedence.
- `test_api_flow.py`: register→vessel→spec(items,freeze)→tender(invite)→portal bid→
  review-accept→leveling→award(memo PDF `%PDF-`)→VO propose/approve→settle; org
  isolation (second org sees nothing); audit rows exist for each mutation;
  sealed bid invisible before deadline.
- `test_auth.py`: bcrypt 72-byte, wrong password 401, role guard.
- `test_parser_golden.py`: §8.4 (skip w/o key).
Target ≈45 tests. Frontend: `next build` in CI is the gate (+ `tsc --noEmit`).

---

## 10. Deploy (after Phase 1 complete + tests green)

1. Backend: `backend/vercel.json` rewrites all→`/api/index`, maxDuration 300, memory
   3009; `api/index.py` exposes the FastAPI app; config falls back to
   `sqlite:////tmp/docktender.db` when `VERCEL` set; lifespan seeds demo org/user/data
   when `DEMO_SEED=1` (default for sqlite) — **cold-start self-healing, same as
   PassagePilot** (README explains ephemerality).
2. Frontend: env `NEXT_PUBLIC_API_URL=https://docktender-api.vercel.app`.
3. Use scratchpad `vdeploy.py` flow (Vercel REST v13 inline files); token comes from
   the user's vault flow as before — if unavailable, ask the user to run the deploy
   or set the token, do not improvise around permission boundaries.
4. `ANTHROPIC_API_KEY`: tell the user to set it in the Vercel dashboard for
   `docktender-api` (precedent: they did this for PassagePilot).
5. Reply with clickable URLs + demo credentials.

---

## 11. Phased execution & acceptance (work top-to-bottom; commit+push per phase)

**Phase 0 — Foundation** (docs/, design/, seed JSONs, models, auth, audit, CI)
✔ `pytest` green (auth+clock); `work_items.json` ≥170 items all with norm_basis;
`yards.json` ≥40 yards; README run instructions work; commit `docktender: phase 0 …`.

**Phase 1a — Engines + API** (§5, §6, demo seed §4.3–4.4)
✔ `test_tec.py` calibration passes; `/api/programme` returns the full mock payload.

**Phase 1b — Frontend shell + Programme** (§7.1–7.2)
✔ Waterline pixel-faithful vs `design_direction.html` (screenshot compare by eye with
Playwright, chromium at `/opt/pw-browsers/...`, `--no-sandbox`, `file://` absolute);
both themes; accent switch live.

**Phase 1c — Specs, Tenders, Leveling, Award** (§7.3–7.4, §8.1–8.3)
✔ Full flow clickable end-to-end on demo data with zero dead ends; leveling matches
§4.4 numbers; award memo PDF downloads.

**Phase 1d — Yards, Executions, Settlements, Settings, Assistant** (§7.5–7.8, §8.4)
✔ Every rail item fully functional; signal picker persists via API; golden tests pass
locally with key.

**Phase 1e — Polish + deploy** (§10)
✔ Live URLs delivered; demo login works from cold start; final README.

Commit style: `docktender: <phase> — <what>` (no model names in commits). Push to
`claude/marine-app-repo-ljpekw` with `git push -u origin`, retry 2/4/8/16s on network
failure only.

---

## 12. Executor guardrails

1. **No invented precision.** Every norm/tariff/duration ships from §4 tables with its
   `norm_basis` label; UI shows "guide norm", never "market rate". New numbers require
   a new row in `DOMAIN_SOURCES.md`.
2. **No dead ends.** A button either works or doesn't exist. Every empty state has a
   real CTA wired to a working flow.
3. **Accent discipline** (§2.4) and **token-only styling** — a hex outside
   `tokens.css` is a review failure. If any chart color changes, re-run the dataviz
   validator (`scripts/validate_palette.js`, mode per theme, surface = card color).
4. **Human-in-the-loop is the product.** AI output is always draft + evidence +
   reviewer stamp. Leveling ignores unreviewed AI lines (§8.1) — this is tested.
5. **Terminology check** — the expert-scrutiny bar: docking plan, wing tanks, sea
   chests, tail shaft survey (keyless), UWILD, Sa 2.5, mh/t, general services,
   dock days, off-hire, VO, final account, growth. Use them correctly or not at all.
6. **Screens match the approved mock** where a mock exists; where none exists
   (specs builder, yards, executions, settlements, settings) derive strictly from the
   component language in `design_direction.html`.
7. Backend errors: structured `{detail}` with correct status; no bare 500s in the
   demo flow. Frontend: loading + error states on every fetch.
8. Do not push to any branch other than the designated one; do not create PRs unless
   asked; keep the Supabase project untouched (separate pending user decision).
