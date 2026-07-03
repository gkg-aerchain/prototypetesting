# DockTender — Deployment Runbook

Two Vercel projects: **`docktender-api`** (Python serverless backend) and
**`docktender`** (Next.js frontend). The backend seeds its demo tenant on cold
start, so no database provisioning is required for the showcase.

Deployment needs a Vercel token (or `vercel login`). Everything is pre-configured;
these are the exact steps.

## 1. Backend — `docktender-api`

```bash
cd docktender/backend
vercel deploy --prod    # or use the Vercel REST API / dashboard import
```

`vercel.json` already sets the Python function (`api/index.py`, maxDuration 300,
memory 3009), rewrites all routes to it, and defaults `DEMO_SEED=1`. On first
request the lifespan creates the schema and seeds the Galene Maritime demo into
`/tmp` SQLite (ephemeral — re-seeds on each cold start).

Note the deployed URL, e.g. `https://docktender-api.vercel.app`. Verify:

```bash
curl https://docktender-api.vercel.app/api/health
# {"status":"ok","seeded":true,"work_items":176,"yards":46}
```

**Optional — enable the AI assistant + bid parser:** in the Vercel dashboard for
`docktender-api`, set `ANTHROPIC_API_KEY`. Without it, `/api/ai/*` returns 503 and
everything else works.

## 2. Frontend — `docktender`

`NEXT_PUBLIC_API_URL` is inlined at build time, so set it before building:

```bash
cd docktender/frontend
vercel env add NEXT_PUBLIC_API_URL production   # → https://docktender-api.vercel.app
vercel deploy --prod
```

Or set the env var in the Vercel dashboard and trigger a redeploy.

## 3. Demo login

```
https://docktender.vercel.app
email:    superintendent@docktender.demo
password: DryDock2026!
```

The demo opens on the Programme command center (Kalymnos Voyager, 134 days to the
36-month rule) with the live tender TND-2026-014 ready to level ($2.90M / $3.04M /
$3.15M).

## Real persistence (beyond the demo)

Set `DATABASE_URL` to a Postgres URL on `docktender-api` and set `DEMO_SEED=0`.
The models are Postgres-ready; run the seed loaders once to populate the library:

```bash
python -m app.seed.build_work_items && python -m app.seed.build_yards
python -c "from app.db import create_all; create_all()"
python -c "from app.db import SessionLocal; from app.seed.loader import load_work_items, load_yards; \
  db=SessionLocal(); load_work_items(db); load_yards(db); db.commit()"
```
