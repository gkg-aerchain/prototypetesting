# DockTender — API Contract

Base prefix `/api`. Auth is JWT bearer (`Authorization: Bearer <token>`). Public
endpoints marked `*`. This document tracks the full planned surface (§6 of the
execution plan); the **Status** column reflects what is live as phases land.

| Method | Path | Purpose | Status |
|---|---|---|---|
| `*GET` | `/api/health` | liveness + seed counts | ✅ Phase 0 |
| `*POST` | `/api/auth/register` | new org + admin user → token | ✅ Phase 0 |
| `*POST` | `/api/auth/login` | credentials → token | ✅ Phase 0 |
| `GET` | `/api/auth/me` | current user profile | ✅ Phase 0 |
| `PATCH` | `/api/me` | update accent / theme / name | ✅ Phase 0 |
| `GET` | `/api/programme` | command-center aggregate | ✅ Phase 1a |
| `GET` | `/api/fleet` · `POST/GET/PATCH/DELETE /api/vessels[/{id}]` | fleet CRUD | ✅ Phase 1a |
| `GET` | `/api/work-items?section=&q=` · `/sections` | canonical library search | ✅ Phase 1a |
| `GET` | `/api/yards?region=&vessel_id=&fits_only=` · `/{id}` | directory + physical-fit filter | ✅ Phase 1a |
| `POST/GET` | `/api/specs[/{id}]` · `/items` · `/copy-forward` · `/freeze` | spec builder | ✅ Phase 1c |
| `POST/GET` | `/api/tenders[/{id}]` · `/invite` · `/issue` · `/clarifications` | tender room | ✅ Phase 1c |
| `POST` | `/api/tenders/{id}/bids` · `/bids/ingest` | portal + AI bid intake | ✅ Phase 1c |
| `GET/PATCH` | `/api/bids/{id}/review` · `/lines/{lid}` · `/sanity-check` | bid review | ✅ Phase 1c |
| `GET/POST` | `/api/tenders/{id}/leveling` · `/evaluate` · `/exposure` | leveling + TEC | ✅ Phase 1c |
| `GET/POST` | `/api/tenders/{id}/award[/preview]` · `GET /api/awards/{id}/memo.pdf` | award | ✅ Phase 1c |
| `GET` | `/api/executions[/{award_id}]` · `POST /vos` · `PATCH /api/vos/{id}` | execution + VO log | ✅ Phase 1d |
| `GET/POST` | `/api/settlements[/{award_id}/close]` | final accounts + scorecards | ✅ Phase 1d |
| `GET/PATCH` | `/api/agents/events` · `/{id}` | review queue | ✅ Phase 1d |
| `POST` | `/api/ai/chat` | assistant (503 without key) | ✅ Phase 1d |

## Live endpoint detail (Phase 0)

### `GET /api/health`
```json
{ "status": "ok", "version": "0.1.0", "seeded": true, "work_items": 176, "yards": 46 }
```

### `POST /api/auth/register`
Body `{ email, password (≥8), full_name?, company? }` → `{ access_token, token_type }`.
Creates a new organization; the first user is its `admin`. `409` if email exists.

### `POST /api/auth/login`
Body `{ email, password }` → `{ access_token }`. `401` on bad credentials.

### `GET /api/auth/me`
→ `{ id, email, full_name, role, accent, theme, org_id }`. `401` unauthenticated.

### `PATCH /api/me`
Body `{ accent?, theme?, full_name? }`. `accent ∈ {cerise,marigold,verdigris,azure,violet}`,
`theme ∈ {system,light,dark}` — `422` otherwise. Returns the updated profile.

## Conventions

- Errors: `{ "detail": "..." }` with an accurate status code. No bare 500s in the demo flow.
- Timestamps ISO-8601 UTC. Money in whole USD unless a `_usd` suffix says otherwise.
- Every mutation to a tenant entity appends an `audit_log` row (actor, action, entity).
- Sealed bids: detail is withheld until the tender `deadline` has passed.
