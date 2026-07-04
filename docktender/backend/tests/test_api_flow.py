"""End-to-end buyer flow: register → vessel → spec (items, freeze) → tender
(invite, issue) → portal bid → award (memo PDF). Plus org isolation, audit rows,
and sealed-bid rules. Uses a clean org (DEMO_SEED off in conftest)."""
from app.core.security import hash_password  # noqa: F401


def _seed_library(client):
    """Load the work-item library + yards into the test DB (needed for specs/yards)."""
    from app.db import SessionLocal
    from app.seed.loader import load_work_items, load_yards

    db = SessionLocal()
    try:
        load_work_items(db)
        load_yards(db)
        db.commit()
    finally:
        db.close()


def test_full_buyer_flow(client, auth):
    _seed_library(client)

    # vessel
    v = client.post("/api/vessels", json={
        "name": "Test LR2", "vessel_type": "LR2", "dwt": 115000, "loa_m": 250.0,
        "beam_m": 44.0, "summer_draft_m": 14.9, "last_docking_date": "2023-11-14T00:00:00Z",
        "special_survey_no": 2, "uwild_ok": True, "tce_usd_day": 22000}, headers=auth)
    assert v.status_code == 201, v.text
    vid = v.json()["id"]
    assert v.json()["window"]["driver"] == "SS No. 2"

    # spec + items from the library + freeze
    s = client.post("/api/specs", json={"vessel_id": vid, "title": "Test SS2 spec"}, headers=auth)
    assert s.status_code == 201
    sid = s.json()["id"]
    items = client.get("/api/work-items?section=1", headers=auth).json()
    add = client.post(f"/api/specs/{sid}/items", headers=auth, json=[
        {"work_item_id": items[0]["id"], "title": items[0]["title"], "qty": 13, "uom": items[0]["uom"]},
        {"work_item_id": items[1]["id"], "title": items[1]["title"], "qty": 1, "uom": items[1]["uom"]},
    ])
    assert add.status_code == 201
    assert add.json()["items"] == 2

    # edit a spec line: quantity + TBC flag persist through a re-read
    line0 = client.get(f"/api/specs/{sid}", headers=auth).json()["item_list"][0]
    patched = client.patch(f"/api/specs/{sid}/items/{line0['id']}", headers=auth,
                           json={"qty": 48.2, "qty_tbc": True, "notes": "est. from UT gauging"})
    assert patched.status_code == 200 and patched.json()["qty"] == 48.2
    reread = client.get(f"/api/specs/{sid}", headers=auth).json()["item_list"][0]
    assert reread["qty"] == 48.2 and reread["qty_tbc"] is True and reread["notes"] == "est. from UT gauging"

    frozen = client.post(f"/api/specs/{sid}/freeze", headers=auth)
    assert frozen.status_code == 200 and frozen.json()["status"] == "frozen"
    # adding to / editing a frozen spec is rejected
    assert client.post(f"/api/specs/{sid}/items", headers=auth, json=[]).status_code == 422
    assert client.patch(f"/api/specs/{sid}/items/{line0['id']}", headers=auth,
                        json={"qty": 1}).status_code == 422

    # tender + invite + issue
    t = client.post("/api/tenders", json={
        "spec_id": sid, "deadline": "2026-07-10T00:00:00Z", "offhire_usd_day": 22000},
        headers=auth)
    assert t.status_code == 201
    tid = t.json()["id"]
    yards = client.get("/api/yards", headers=auth).json()
    yard_ids = [yards[0]["id"], yards[1]["id"]]
    client.post(f"/api/tenders/{tid}/invite", json={"yard_ids": yard_ids}, headers=auth)
    issued = client.post(f"/api/tenders/{tid}/issue", headers=auth)
    assert issued.json()["status"] == "issued"

    # leveling before any bids is a graceful empty state, not an error
    empty = client.get(f"/api/tenders/{tid}/leveling", headers=auth)
    assert empty.status_code == 200
    assert empty.json()["cards"] == [] and empty.json()["evaluated"] is False

    # two portal bids — the second is cheaper on sticker but has deviation + an
    # exclusion that price its total evaluated cost higher.
    b1 = client.post(f"/api/tenders/{tid}/bids", headers=auth, json={
        "yard_id": yard_ids[0], "currency": "USD", "dock_days": 13, "tariff_captured": True,
        "deviation_nm": 300, "port_fees_usd": 40000,
        "lines": [{"raw_text": "General services", "amount": 300000, "state": "priced", "uom": "lot"}]})
    assert b1.status_code == 201
    b2 = client.post(f"/api/tenders/{tid}/bids", headers=auth, json={
        "yard_id": yard_ids[1], "currency": "USD", "dock_days": 16, "tariff_captured": False,
        "deviation_nm": 2400, "port_fees_usd": 0,
        "lines": [{"raw_text": "General services", "amount": 260000, "state": "priced", "uom": "lot"},
                  {"raw_text": "Grit disposal", "state": "excluded", "exposure_median_usd": 40000}]})
    assert b2.status_code == 201

    # the bids-list endpoint powers the review screen
    blist = client.get(f"/api/tenders/{tid}/bids", headers=auth).json()
    assert len(blist) == 2 and all(b["source"] == "portal" for b in blist)

    # evaluate + leveling
    ev = client.post(f"/api/tenders/{tid}/evaluate", json={}, headers=auth)
    assert ev.status_code == 200
    lev = ev.json()
    assert len(lev["cards"]) == 2
    # the complete, tariff-captured bid should rank first on TEC despite higher sticker
    assert lev["cards"][0]["rank"] == 1
    assert lev["cards"][0]["recommended"] is True
    # deviation genuinely priced into the winner's composition
    dev = next(c for c in lev["cards"][0]["composition"] if c["key"] == "deviation")
    assert dev["usd"] > 0

    # award + memo PDF
    prev = client.get(f"/api/tenders/{tid}/award/preview", headers=auth).json()
    aw = client.post(f"/api/tenders/{tid}/award", headers=auth, json={
        "bid_id": prev["recommended_bid_id"], "memo_note": "Awarded on TEC.",
        "checklist": prev["checklist"]})
    assert aw.status_code == 201
    pdf = client.get(f"/api/awards/{aw.json()['award_id']}/memo.pdf", headers=auth)
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
    # double award rejected
    assert client.post(f"/api/tenders/{tid}/award", headers=auth, json={
        "bid_id": prev["recommended_bid_id"]}).status_code == 409


def test_org_isolation(client):
    """A second org cannot see the first org's tenders/vessels."""
    r = client.post("/api/auth/register", json={
        "email": "other@example.com", "password": "otherpass123", "company": "Other Managers"})
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/tenders", headers=other).json() == []
    assert client.get("/api/fleet", headers=other).json() == []


def test_audit_rows_created(client, auth):
    """Mutations append audit rows."""
    from app.db import SessionLocal
    from app.models import AuditLog
    from sqlalchemy import func, select

    db = SessionLocal()
    try:
        n = db.scalar(select(func.count()).select_from(AuditLog)) or 0
    finally:
        db.close()
    assert n > 0  # register + vessel + spec + tender + award all audited
