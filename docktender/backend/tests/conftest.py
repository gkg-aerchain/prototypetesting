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
    db_path = os.environ["DATABASE_URL"].replace("sqlite:///", "")
    if os.path.exists(db_path):
        os.remove(db_path)
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    r = client.post("/api/auth/register", json={
        "email": "supt@example.com", "password": "testpass123",
        "full_name": "Test Supt", "company": "Test Managers"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
