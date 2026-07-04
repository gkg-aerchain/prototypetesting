"""The moat: Total Evaluated Cost must be genuinely computed from the stored bid
data, and the live /evaluate endpoint must reproduce the seeded evaluation exactly
(the earlier build hardcoded the seed numbers and /evaluate disagreed with them)."""
import pytest
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.seed.loader import DEMO_EMAIL, DEMO_PASSWORD


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("lev") / "demo.db"
    settings.database_url = f"sqlite:///{db_file}"
    settings.demo_seed = True
    import sqlalchemy

    from app import db as dbmod

    dbmod.engine.dispose()
    dbmod.engine = sqlalchemy.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}, future=True)
    dbmod.SessionLocal.configure(bind=dbmod.engine)
    with TestClient(app) as c:
        tok = c.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
                     ).json()["access_token"]
        yield c, {"Authorization": f"Bearer {tok}"}
    settings.demo_seed = False


def _tender_id(c, h):
    tenders = c.get("/api/tenders", headers=h).json()
    return next(t["id"] for t in tenders if t["ref"] == "TND-2026-014")


# The calibrated targets, in dollars (±$1k tolerance).
TARGETS = {"Drydocks World — Dubai": 2_900_000,
           "Seatrium Admiralty Yard": 3_040_000,
           "Besiktas Shipyard (Yalova)": 3_150_000}


def _cards_by_yard(payload):
    return {card["yard"]: card for card in payload["cards"]}


def test_seeded_leveling_hits_calibrated_tec(demo):
    c, h = demo
    tid = _tender_id(c, h)
    payload = c.get(f"/api/tenders/{tid}/leveling", headers=h).json()
    cards = _cards_by_yard(payload)
    for yard, target in TARGETS.items():
        assert abs(cards[yard]["tec_usd"] - target) < 1000, (yard, cards[yard]["tec_usd"])
    # Sticker-vs-TEC inversion: the cheapest sticker is the worst total cost.
    lowest_sticker = min(payload["cards"], key=lambda k: k["sticker_usd"])
    highest_tec = max(payload["cards"], key=lambda k: k["tec_usd"])
    assert lowest_sticker["yard"] == "Besiktas Shipyard (Yalova)"
    assert highest_tec["yard"] == "Besiktas Shipyard (Yalova)"
    # Recommendation is the lowest clean TEC, not the crit-flagged cheapest.
    rec = next(card for card in payload["cards"] if card["recommended"])
    assert rec["yard"] == "Drydocks World — Dubai"
    assert rec["rank"] == 1


def test_live_evaluate_reproduces_seeded_numbers(demo):
    """Re-running /evaluate over the stored bids must land on the same figures —
    proving the numbers are computed, not hardcoded into the seed."""
    c, h = demo
    tid = _tender_id(c, h)
    before = _cards_by_yard(c.get(f"/api/tenders/{tid}/leveling", headers=h).json())
    reevaluated = c.post(f"/api/tenders/{tid}/evaluate", headers=h, json={})
    assert reevaluated.status_code == 200, reevaluated.text
    after = _cards_by_yard(reevaluated.json())
    for yard in TARGETS:
        assert abs(after[yard]["tec_usd"] - before[yard]["tec_usd"]) < 1.0, yard
        # And each component is stable, not just the total.
        for comp_b, comp_a in zip(before[yard]["composition"], after[yard]["composition"]):
            assert abs(comp_b["usd"] - comp_a["usd"]) < 1.0, (yard, comp_b["key"])
