"""DockTender FastAPI application.

Lifespan creates tables and — when DEMO_SEED is on and the database is SQLite —
seeds the canonical library and the demo tenant. This makes the Vercel deployment
self-healing across cold starts (the /tmp SQLite file is ephemeral), exactly like
PassagePilot.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .db import SessionLocal, create_all
from .routers import auth, health, me


_seeded = False


def _ensure_seeded() -> None:
    """Create schema and seed the demo once per process.

    Runs from the lifespan (local/uvicorn/pytest) and, because Vercel's
    serverless ASGI adapter does not reliably fire lifespan startup, also
    lazily on the first HTTP request. ``seed_all`` is idempotent, so a double
    invocation is harmless.
    """
    global _seeded
    if _seeded:
        return
    create_all()
    if settings.demo_seed and settings.is_sqlite:
        from .seed.loader import seed_all

        db = SessionLocal()
        try:
            seed_all(db)
        finally:
            db.close()
    _seeded = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_seeded()
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _seed_on_first_request(request, call_next):
    if not _seeded:
        _ensure_seeded()
    return await call_next(request)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(me.router)


# Additional routers (fleet, programme, specs, tenders, bids, leveling, awards,
# executions, settlements, yards, ai) are registered as they land in Phase 1.
def _register_optional() -> None:
    for modname in (
        "fleet", "programme", "workitems", "yards", "specs", "tenders",
        "bids", "leveling", "awards", "executions", "settlements", "ai",
    ):
        try:
            mod = __import__(f"app.routers.{modname}", fromlist=["router"])
            app.include_router(mod.router)
        except ModuleNotFoundError:
            continue


_register_optional()
