"""Test fixtures. Each test module gets an isolated SQLite file, DEMO_SEED off so
the library/demo tenant don't interfere with unit assertions (individual tests seed
what they need)."""
import os
import tempfile

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.gettempdir()}/dt_test.db"
os.environ["DEMO_SEED"] = "0"

from app.core.config import settings  # noqa: E402

settings.database_url = os.environ["DATABASE_URL"]
settings.demo_seed = False

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    # Rebind the global engine to a fresh dt_test.db for this module. Other modules
    # (e.g. test_programme) rebind the engine to their own DB, so we reset it here
    # and dispose any pooled connections to the previous file before removing it.
    import sqlalchemy

    from app import db as dbmod

    url = os.environ["DATABASE_URL"]
    settings.database_url = url
    db_path = url.replace("sqlite:///", "")
    dbmod.engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)
    dbmod.engine = sqlalchemy.create_engine(
        url, connect_args={"check_same_thread": False}, future=True)
    dbmod.SessionLocal.configure(bind=dbmod.engine)
    with TestClient(app) as c:
        yield c
    dbmod.engine.dispose()


@pytest.fixture(scope="module")
def auth(client):
    r = client.post("/api/auth/register", json={
        "email": "supt@example.com", "password": "testpass123",
        "full_name": "Test Supt", "company": "Test Managers"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
