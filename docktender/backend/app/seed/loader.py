"""Load the canonical library (work items, yards) and the demo tenant into the DB.
Idempotent: safe to call on every boot (skips when already populated)."""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import hash_password
from ..models import Dock, Organization, User, WorkItem, Yard

_HERE = Path(__file__).parent

DEMO_ORG_NAME = "Galene Maritime"
DEMO_EMAIL = "superintendent@docktender.demo"
DEMO_PASSWORD = "DryDock2026!"


def _load_json(name: str):
    return json.loads((_HERE / name).read_text())


def load_work_items(db: Session) -> int:
    if db.scalar(select(WorkItem).limit(1)):
        return 0
    items = _load_json("work_items.json")
    for it in items:
        db.add(WorkItem(
            code=it["code"], section=it["section"], section_name=it["section_name"],
            title=it["title"], uom=it["uom"], norm_value=it["norm_value"],
            norm_unit=it["norm_unit"], norm_basis=it["norm_basis"],
            factors_json=it.get("factors", {}), typical=it.get("typical", True),
        ))
    db.flush()
    return len(items)


def load_yards(db: Session) -> int:
    if db.scalar(select(Yard).limit(1)):
        return 0
    yards = _load_json("yards.json")
    for y in yards:
        yard = Yard(
            name=y["name"], country=y["country"], region=y["region"],
            labor_rate_band=y["labor_rate_band"], lat=y["lat"], lon=y["lon"],
            notes=y.get("notes", ""),
        )
        db.add(yard)
        db.flush()
        for d in y["docks"]:
            db.add(Dock(
                yard_id=yard.id, name=d["name"], kind=d["kind"], length_m=d["length_m"],
                beam_m=d["beam_m"], depth_over_blocks_m=d["depth_over_blocks_m"],
                max_dwt=d["max_dwt"], cranes_json=d.get("cranes_json", []),
            ))
    db.flush()
    return len(yards)


def ensure_demo_org(db: Session) -> Organization:
    org = db.scalar(select(Organization).where(Organization.name == DEMO_ORG_NAME))
    if not org:
        org = Organization(name=DEMO_ORG_NAME, kind="manager")
        db.add(org)
        db.flush()
    return org


def ensure_demo_user(db: Session, org: Organization) -> User:
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if not user:
        user = User(
            org_id=org.id, email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD),
            full_name="S. Nair", role="admin", accent="cerise", theme="dark",
        )
        db.add(user)
        db.flush()
    return user


def seed_all(db: Session) -> dict:
    """Load library + demo tenant. Returns a small summary for /health."""
    wi = load_work_items(db)
    yd = load_yards(db)
    org = ensure_demo_org(db)
    ensure_demo_user(db, org)
    # Full demo fleet/tender fixtures (Phase 1a) live in demo.py; import lazily so
    # Phase 0 works even before that module exists.
    try:
        from . import demo

        demo.seed_demo_data(db, org)
    except Exception:  # pragma: no cover - demo fixtures optional at this stage
        pass
    db.commit()
    return {"work_items": wi, "yards": yd, "org": org.name}
