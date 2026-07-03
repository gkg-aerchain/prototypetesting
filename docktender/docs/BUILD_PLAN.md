# DockTender — Build Plan

Companion to PRD.md · v0.1 · July 2026

## Architecture (proven pattern, reused from PassagePilot)

```
frontend/   Next.js 14 + TypeScript + Tailwind — tender room UI, leveling matrix,
            yard workbench. Same shell/design system as PassagePilot (dark maritime).
backend/    FastAPI (Python 3.11) — domain engines + REST API
            engines: normalization (unit/FX/taxonomy mapping), TEC, benchmark norms,
            estimate engine (yard side), VO pricing
            ai/: Claude (claude-opus-4-8) with structured outputs for quote parsing,
            spec drafting, sanity checks — always human-reviewed
db          PostgreSQL from day 1 (NOT SQLite: sealed bids + multi-tenancy are
            core, ephemeral data is unacceptable here). Supabase or RDS.
services    Reuse PassagePilot routing API for deviation distance/fuel in TEC.
infra       Docker compose, GitHub Actions CI, Vercel (frontend) + persistent
            backend host; pytest + Playwright checks in CI.
```

**Why Postgres is non-negotiable this time:** tender integrity (sealed bids, audit log) is the product's trust foundation. Row-level security by organization; bid rows carry `sealed_until`; every tender mutation appends to an audit table.

## Data model (core tables)

```
organizations(kind: manager|yard), users(role, org)
vessels(particulars, last_dockings[], survey_dates, edd_enrolled, uwild_ok)
yards(org_fk), docks(yard, length, beam, depth_over_blocks, cranes, notes)
work_items(canonical taxonomy: code, section, title, uom, norm_mh, norm_factors)
specifications(vessel, docking_window, status: draft|frozen), spec_items(work_item fk,
  qty_est, qty_tbc flag, origin: class|defect|owner, attachments)
tenders(spec, deadline, sealed, status), invitations(tender, yard, status)
clarifications(tender, question, answer, addendum_no)
bids(tender, yard, revision, currency, validity, dock_offered, dates, terms,
  tariff_doc fk, sealed_until), bid_lines(bid, spec_item fk nullable, raw_text,
  uom, qty, rate, amount, included|excluded|unpriced, assumptions, ai_confidence)
tariffs(yard, doc, extracted_lines[])   -- captured pre-award, prices VOs later
evaluations(tender, weights, fx_date), tec_components(bid, deviation, offhire,
  vo_risk, adjustments)
awards(tender, bid, memo_doc, checklist_state)
variation_orders(award, spec_item?, description, qty, tariff_line?, price,
  state: proposed|approved|disputed), final_accounts(award, lines, growth_pct)
yard_scores(yard, docking, growth_pct, overrun_days, quality, hse)
audit_log(org, actor, action, entity, ts)
```

## Phasing

**Phase 0 — Foundation (repo + seed data)**
- Repo `dock-tender` (user creates on GitHub, same flow as marine-app), docs in `/docs` (this PRD + ARCHITECTURE + API contract)
- Seed canonical work-item library (~150–250 items across the 10 spec sections, with UoM and Butler-derived benchmark norms clearly labeled as guide values)
- Seed yard directory (~40–60 major repair yards with dock dimensions: Sembcorp/Seatrium, Drydocks World Dubai, ASRY, Bahrain, Oman Drydock, Colombo Dockyard, Cochin, Hindustan, Chittagong DD, COSCO/CUD yards, Yiu Lian, HRDD, Besiktas, Tuzla yards, Gibdock, Astander, Damen yards, Remontowa, Fayard, Blohm+Voss, Grand Bahama, Detyens, Vigor…) — curated planning-grade data like PassagePilot's ports.json
- Auth/tenancy skeleton with RLS + audit log

**Phase 1 — Tender room MVP (buyer side)** ← first demo to the expert
1. Vessel registry + docking-window planner (36-month/UWILD/EDD logic)
2. Spec builder (library picker, Excel import, copy-forward, freeze/versioning)
3. Yard directory + physical-fit filter; tender creation + invitations + Q&A/addenda
4. Bid intake: structured portal form AND AI PDF/Excel ingestion → review screen (accept/remap per line) — build the review UX first, the parser second
5. Leveling matrix (canonical grid, FX, exclusions diff, benchmark deltas, unpriced-exposure panel)
6. TEC ranking (deviation via PassagePilot routing API; off-hire input; VO-risk heuristic v1 = unpriced items × tariff + growth factor default)
7. Award memo PDF + contract checklist + tariff vault
8. Demo dataset: 1 fleet (5 vessels), 1 live tender (Aframax special survey docking, 3 yard bids — one cheap-but-excluding, one expensive-but-complete, one mid — so the TEC story lands in the demo)

**Phase 2 — Execution & settlement:** VO log priced from captured tariff, approvals/disputes, cost curve, final account reconciliation, yard scorecards, fleet KPI dashboard.

**Phase 3 — Yard workbench:** tender inbox, tariff-book upload/extraction, estimate engine (norms × labour rate × per-customer commercial factor with margin view), structured bid composer, dock slot board.

**Phase 4 — Network:** public yard profiles, availability signals, anonymized benchmarks, reputation.

## AI implementation notes
- Quote parsing: Claude structured outputs against `bid_lines` schema; chunk long PDFs; per-line confidence; UI enforces human confirmation below threshold. Golden-set eval harness (10 synthetic yard quotes in varied formats) in CI.
- Spec drafting + sanity checker + clarification drafter: same tool-loop pattern proven in PassagePilot's assistant.
- Never present AI mappings as settled fact in tender records — reviewer identity stamped on every accepted line (audit).

## Risks & mitigations
- **Expert credibility** → every domain number in-app traceable to the source register; benchmarks labeled "guide norms (Butler 2012), not yard tariffs."
- **Two-sided cold start** → Phase 1 is fully valuable single-sided (AI ingestion means no yard participation needed); yards onboard later because structured bidding is free and faster for them.
- **Bid confidentiality doubts** → sealed-bid mechanics + audit log visible in UI from day 1.
- **Normalization accuracy** → human-in-the-loop review screen is the product; AI only accelerates it.
- **Competitive overlap (MariApps/BASSnet)** → never market "first quote comparison"; market normalization depth, TEC, tariff-anchored VO control, two-sidedness.

## Immediate next steps
1. User creates `dock-tender` repo (GitHub app access, same as marine-app)
2. Commit PRD + this plan; scaffold monorepo
3. Phase 0 seed data authoring (work-item taxonomy is the critical path — it is the canonical grid everything maps to)
4. Phase 1 build in the PassagePilot pattern (docs → backend engines → API → frontend → tests → deploy)
