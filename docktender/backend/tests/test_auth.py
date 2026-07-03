"""Auth: bcrypt (incl. >72-byte passwords), register/login/me, role guard, seeding."""
from app.core.security import hash_password, verify_password
from app.seed.loader import seed_all


def test_bcrypt_roundtrip_and_72_byte():
    h = hash_password("testpass123")
    assert verify_password("testpass123", h)
    assert not verify_password("wrong", h)
    # A >72-byte password must hash without error and verify by its first 72 bytes.
    long_pw = "a" * 100
    h2 = hash_password(long_pw)
    assert verify_password("a" * 72, h2)  # first 72 bytes match


def test_register_login_me(client, auth):
    me = client.get("/api/auth/me", headers=auth).json()
    assert me["email"] == "supt@example.com"
    assert me["role"] == "admin"  # first user of a new org
    assert me["accent"] == "cerise"


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"email": "supt@example.com", "password": "nope"})
    assert r.status_code == 401


def test_duplicate_register_conflicts(client):
    r = client.post("/api/auth/register", json={
        "email": "supt@example.com", "password": "testpass123", "full_name": "Dup"})
    assert r.status_code == 409


def test_patch_me_accent_theme(client, auth):
    r = client.patch("/api/me", json={"accent": "verdigris", "theme": "dark"}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["accent"] == "verdigris" and body["theme"] == "dark"
    # invalid accent rejected
    assert client.patch("/api/me", json={"accent": "chartreuse"}, headers=auth).status_code == 422


def test_seed_loads_library(client):
    """seed_all loads the full library + demo tenant into the same test DB."""
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        summary = seed_all(db)
    finally:
        db.close()
    # library counts (>=170 work items, >=40 yards per the acceptance bar)
    h = client.get("/api/health").json()
    assert h["seeded"] is True
    assert h["work_items"] >= 170
    assert h["yards"] >= 40


def test_demo_login_after_seed(client):
    """The seeded demo superintendent can log in with the documented credentials."""
    from app.seed.loader import DEMO_EMAIL, DEMO_PASSWORD

    r = client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert r.status_code == 200
