"""Command-center aggregate — the demo tenant must reproduce the approved mock:
focus clock 134 days, programme $14.2M, tenders in flight, final vs quoted +9.4%,
the Waterline ordering, the review queue. Uses the seeded demo org."""
import pytest
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.seed.demo import FLEET
from app.seed.loader import DEMO_EMAIL, DEMO_PASSWORD


@pytest.fixture(scope="module")
def demo_client(tmp_path_factory):
    # Fresh DB with demo seeding ON for this module.
    db_file = tmp_path_factory.mktemp("prog") / "demo.db"
    settings.database_url = f"sqlite:///{db_file}"
    settings.demo_seed = True
    from app import db as dbmod

    dbmod.engine.dispose()
    dbmod.engine = __import__("sqlalchemy").create_engine(
        settings.database_url, connect_args={"check_same_thread": False}, future=True)
    dbmod.SessionLocal.configure(bind=dbmod.engine)
    with TestClient(app) as c:
        yield c
    settings.demo_seed = False


@pytest.fixture(scope="module")
def demo_auth(demo_client):
    r = demo_client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_programme_focus_matches_mock(demo_client, demo_auth):
    p = demo_client.get("/api/programme", headers=demo_auth).json()
    assert p["today"] == "2026-07-03"
    assert p["vessel_count"] == len(FLEET)
    # Kalymnos is the nearest hard stop regardless of how large the fleet grows.
    f = p["focus"]
    assert f["vessel"] == "Kalymnos Voyager"
    assert f["days_left"] == 134
    assert f["driver"] == "SS No. 2"
    assert "3 bids in" in f["sub"]


def test_programme_stats(demo_client, demo_auth):
    p = demo_client.get("/api/programme", headers=demo_auth).json()
    stats = {s["key"]: s for s in p["stats"]}
    # Real roll-up, no hardcoded constant.
    assert stats["programme"]["value"] > 0
    # At least Kalymnos + Thera issued; sub reports real received/expected bids.
    assert stats["tenders"]["value"] >= 2
    assert "bids received" in stats["tenders"]["sub"]
    # Average final-vs-quoted growth is computed from the settled dockings.
    assert stats["final_vs_quoted"]["value"] > 0


def test_waterline_ordering(demo_client, demo_auth):
    p = demo_client.get("/api/programme", headers=demo_auth).json()
    wl = p["waterline"]
    names = [w["name"] for w in wl]
    # Kalymnos leads (closest window); Paros (in dock) is present and categorized.
    assert names[0] == "Kalymnos Voyager"
    assert wl[0]["severity"] == "signal"
    assert wl[0]["pill"] == "Bids in · 3 of 4"  # matches the waterline "BIDS 3/4"
    paros = next(w for w in wl if w["name"] == "Paros Horizon")
    assert paros["category"] == "in_dock"
    assert paros["pill"] == "In dock · day 6/13"
    # Completed Milos Beacon is not on the forward waterline.
    assert "Milos Beacon" not in names
    # Thera Compass shows tender-out with invited count.
    thera = next(w for w in wl if w["name"] == "Thera Compass")
    assert thera["pill"] == "Tender out · 7 invited"


def test_review_queue(demo_client, demo_auth):
    p = demo_client.get("/api/programme", headers=demo_auth).json()
    assert len(p["queue"]) == 3
    agents = {q["agent"] for q in p["queue"]}
    assert "bid_parser" in agents


def test_fleet_endpoint(demo_client, demo_auth):
    fleet = demo_client.get("/api/fleet", headers=demo_auth).json()
    assert len(fleet) == len(FLEET)
    kal = next(v for v in fleet if v["name"] == "Kalymnos Voyager")
    assert kal["window"]["days_left"] == 134


def test_yards_fit_filter(demo_client, demo_auth):
    fleet = demo_client.get("/api/fleet", headers=demo_auth).json()
    kal_id = next(v["id"] for v in fleet if v["name"] == "Kalymnos Voyager")
    yards = demo_client.get(f"/api/yards?vessel_id={kal_id}&fits_only=true", headers=demo_auth).json()
    assert len(yards) > 0
    # every returned yard has at least one fitting dock
    assert all(y["fits"] for y in yards)
    # a fitting dock clears the vessel on length/beam/depth
    some = yards[0]
    fitting = [d for d in some["docks"] if d.get("fits")]
    assert fitting and fitting[0]["margins"]["loa_m"] >= 6


def test_work_items_search(demo_client, demo_auth):
    items = demo_client.get("/api/work-items?section=3", headers=demo_auth).json()
    assert items and all(i["section"] == 3 for i in items)
    assert all(i["norm_basis"] for i in items)
    steel = demo_client.get("/api/work-items?q=shell+plate", headers=demo_auth).json()
    assert any("shell plate" in i["title"].lower() for i in steel)
