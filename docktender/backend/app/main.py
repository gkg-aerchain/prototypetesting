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


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all()
    if settings.demo_seed and settings.is_sqlite:
        from .seed.loader import seed_all

        db = SessionLocal()
        try:
            seed_all(db)
        finally:
            db.close()
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
