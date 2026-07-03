# DockTender — Architecture

v0.1 · Phase 0. Companion to `EXECUTION_PLAN.md` (the authoritative build spec).

## Shape

Two-tier, same proven pattern as PassagePilot:

```
frontend/   Next.js 14 (App Router) + TypeScript + Tailwind.
            Token-driven design system (design/tokens.css): dark navy "bridge chrome"
            rail/masthead over a light "working deck". Theme (light/dark) and the
            signal accent (5 options) are per-user settings carried on <html
            data-theme data-accent>, hydrated from /api/auth/me.
backend/    FastAPI (Python 3.11) + SQLAlchemy 2.0.
            Pure-function domain engines (engines/), thin routers (routers/),
            AI helpers (ai/) with human-in-the-loop review.
db          SQLAlchemy models are Postgres-ready (string UUID pks, JSON columns,
            indexed FKs, org_id on every tenant table) but run on SQLite for the
            demo. DATABASE_URL selects the backend; Vercel falls back to ephemeral
            /tmp SQLite and re-seeds at boot.
```

## Backend layers

- **models.py** — the full schema (§3 of the execution plan). Every tenant-scoped
  table carries `org_id`.
- **deps.py** — `get_current_user` (JWT) is the org-scope guard; routers filter every
  query by `user.org_id`. This is the row-level-security stand-in for the demo; a
  production Postgres deployment would enforce it with real RLS policies.
- **core/audit.py** — `audit(...)` appends an `audit_log` row; called on every
  mutation to specs / tenders / bids / awards / variation orders.
- **engines/** — deterministic, fully unit-tested, no I/O:
  - `clock.py` — 36-month docking-window rule, drivers, severity.
  - `normalization.py` — canonical bid leveling, FX freeze, unit conversion.
  - `norms.py` — guide-norm deviation flags (the "estimator" checks).
  - `tec.py` — Total Evaluated Cost = normalized + deviation + off-hire + VO exposure.
  - `exposure.py` — itemized VO-risk model backing the TEC's exposure term.
  - `awards.py` — award-memo PDF (reportlab).
- **ai/** — `bid_parser` (quote → bid_lines), `sanity` (norms engine, labelled as
  the Sanity Checker agent), `clarifier`, `assistant`. All AI output is draft +
  evidence + reviewer stamp; leveling ignores unreviewed AI lines.
- **routers/** — one module per resource; `main.py` registers them and, on lifespan
  startup, creates tables and seeds the library + demo tenant when SQLite + DEMO_SEED.

## Trust model

- **Tenancy** — `org_id` filter on every query; second-org isolation is tested.
- **Sealed bids** — a bid carries `sealed_until`; the API refuses to expose bid detail
  before the tender deadline (tested), and the assistant will not read a sealed bid.
- **Audit** — every mutation is logged with actor, action, entity; visible in-app.
- **AI is assistive only** — a reviewer identity is stamped on every accepted bid line.

## Seed data

`seed/build_work_items.py` and `seed/build_yards.py` encode the domain norms and yard
directory in code (with source labels) and emit the JSON the loader ingests. CI
regenerates them and fails if the committed JSON drifts. Guide values are
planning-grade and always carry a `norm_basis` — see `DOMAIN_SOURCES.md`.

## Deploy

Frontend and backend deploy as two Vercel projects (`docktender`, `docktender-api`).
The backend is a Python serverless function (`api/index.py` exposing the ASGI app,
all routes rewritten to it). SQLite on `/tmp` is ephemeral, so the lifespan re-seeds
on cold start — the demo is self-healing. `ANTHROPIC_API_KEY` is set in the Vercel
dashboard; without it the assistant returns 503 and the rest of the app is unaffected.
