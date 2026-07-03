# DockTender

**The tender room for dry-docking.** A two-sided dry-docking procurement platform —
ship-manager (buyer) side first: docking-window planning → specification → tender →
AI-normalized bid leveling on **Total Evaluated Cost** → award → variation-order and
final-account control.

Not "the first quote-comparison tool" — the competitive edge is *normalization depth*
(one canonical grid, AI-parsed quotes, exclusions surfaced), *Total Evaluated Cost*
(sticker + deviation + off-hire + VO exposure), and *tariff-anchored VO control*.

> Status: **Phase 0 (foundation) complete.** Backend scaffold, canonical work-item
> library (176 items) and yard directory (46 yards), data model, auth + audit, seed +
> tests + CI. Engines, API, and the frontend land in Phase 1 — see
> `docs/EXECUTION_PLAN.md`.

## Repository layout

```
docktender/
  docs/          PRD, build plan, EXECUTION_PLAN (authoritative), ARCHITECTURE,
                 API contract, DOMAIN_SOURCES (every guide norm + its source)
  design/        approved design direction (v6), tokens.css, inlined Geist fonts
  backend/       FastAPI + SQLAlchemy — engines, routers, ai, seed, tests
  frontend/      Next.js 14 + TypeScript + Tailwind (Phase 1b)
```

## Run the backend (local)

```bash
cd docktender/backend
pip install -r requirements.txt
uvicorn app.main:app --reload            # http://localhost:8000
```

On first boot (SQLite + `DEMO_SEED=1`, both defaults) it creates the schema and seeds
the canonical library plus the **Galene Maritime** demo tenant.

Check it: `curl localhost:8000/api/health` → `{"status":"ok","seeded":true,...}`

### Demo login

```
email:    superintendent@docktender.demo
password: DryDock2026!
```

### Tests

```bash
cd docktender/backend
python -m pytest
```

### Regenerate seed data

The work-item library and yard directory are generated from documented builders
(the domain norms live in code, with source labels):

```bash
python -m app.seed.build_work_items   # -> app/seed/work_items.json
python -m app.seed.build_yards        # -> app/seed/yards.json
```

CI fails if the committed JSON drifts from the builders.

## Docker

```bash
ANTHROPIC_API_KEY=sk-... docker compose up
```

Backend on `:8000`, frontend on `:3000` (once scaffolded).

## Deploy (Phase 1e)

Two Vercel projects: `docktender` (frontend) and `docktender-api` (Python serverless,
`backend/api/index.py`). SQLite on `/tmp` is ephemeral, so the backend re-seeds the
demo on cold start. Set `ANTHROPIC_API_KEY` in the `docktender-api` project for the
assistant (without it, `/api/ai/chat` returns 503 and everything else works).

## Domain integrity

Every norm, rate, and duration in the app is **planning-grade** and carries a source
label — see `docs/DOMAIN_SOURCES.md`. The product shows guide norms for leveling
deltas, never presents a number as a yard tariff, and keeps AI output as
draft-plus-evidence with a human reviewer stamped on every accepted bid line.
