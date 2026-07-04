"""Executions, settlements, and the AI 503 path — against the seeded demo tenant."""
import pytest
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.seed.loader import DEMO_EMAIL, DEMO_PASSWORD


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("exec") / "demo.db"
    settings.database_url = f"sqlite:///{db_file}"
    settings.demo_seed = True
    import sqlalchemy

    from app import db as dbmod

    dbmod.engine.dispose()
    dbmod.engine = sqlalchemy.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}, future=True)
    dbmod.SessionLocal.configure(bind=dbmod.engine)
    with TestClient(app) as c:
        tok = c.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}).json()["access_token"]
        yield c, {"Authorization": f"Bearer {tok}"}
    settings.demo_seed = False


def test_executions_paros_in_dock(demo):
    c, h = demo
    execs = c.get("/api/executions", headers=h).json()
    paros = next(e for e in execs if e["vessel"] == "Paros Horizon")
    assert paros["in_dock"] and paros["dock_day"] == 6 and paros["dock_total"] == 13
    assert paros["vo_count"] == 8 and paros["vo_open"] == 2
    # VO-07 is over tariff by $4,100
    vo7 = next(v for v in paros["vos"] if v["vo_no"] == "VO-07")
    assert vo7["over_tariff_usd"] == 4100.0 and vo7["state"] == "proposed"


def test_vo_approve(demo):
    c, h = demo
    execs = c.get("/api/executions", headers=h).json()
    paros = next(e for e in execs if e["vessel"] == "Paros Horizon")
    vo = next(v for v in paros["vos"] if v["state"] == "proposed")
    r = c.patch(f"/api/vos/{vo['id']}", json={"state": "approved", "reason": "within scope"}, headers=h)
    assert r.status_code == 200 and r.json()["state"] == "approved"


def test_settlements_and_scorecards(demo):
    c, h = demo
    s = c.get("/api/settlements", headers=h).json()
    # multiple settled dockings, averaged; Milos Beacon among them at +9.4%
    assert s["kpi"]["settled_count"] >= 3
    assert s["kpi"]["avg_growth_pct"] > 0
    assert any(a["vessel"] == "Milos Beacon" and a["growth_pct"] == 9.4 for a in s["accounts"])
    # scorecards ranked best-growth first; Besiktas worst
    assert s["scorecards"][0]["avg_growth_pct"] <= s["scorecards"][-1]["avg_growth_pct"]
    assert any("Besiktas" in sc["yard"] for sc in s["scorecards"])


def test_ai_chat_503_without_key(demo):
    c, h = demo
    r = c.post("/api/ai/chat", headers=h, json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 503


def test_agent_events_queue(demo):
    c, h = demo
    q = c.get("/api/agents/events?needs_decision=true", headers=h).json()
    assert len(q) == 3
    # decide one
    r = c.patch(f"/api/agents/events/{q[0]['id']}", headers=h)
    assert r.json()["needs_decision"] is False
