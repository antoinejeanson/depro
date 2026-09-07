from datetime import datetime, timedelta

from app.models import Session

EMAIL = "ada@example.com"
PASSWORD = "supersecret1"


def _register(client, email: str = EMAIL, password: str = PASSWORD):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_register_creates_user_and_session(client):
    r = _register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == EMAIL
    assert "id" in body
    assert "depro_session" in r.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


def test_register_duplicate_email_rejected(client):
    assert _register(client).status_code == 201
    assert _register(client).status_code == 409


def test_register_normalizes_email(client):
    assert _register(client, email="Ada@Example.COM").status_code == 201
    # Same address again, different casing: still a duplicate.
    assert _register(client, email="ada@example.com").status_code == 409


def test_register_short_password_rejected(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "short"})
    assert r.status_code == 422


def test_login_success(client):
    _register(client)
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200
    assert r.json()["email"] == EMAIL
    assert "depro_session" in r.cookies


def test_login_wrong_password(client):
    _register(client)
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": "wrongpassword"})
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_garbage_cookie(client):
    client.cookies.set("depro_session", "not-a-real-token")
    assert client.get("/api/auth/me").status_code == 401


def test_logout_invalidates_session(client):
    _register(client)
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_logout_without_cookie_is_fine(client):
    assert client.post("/api/auth/logout").status_code == 204


def test_expired_session_rejected(client, test_db):
    _register(client)
    db = test_db()
    db.query(Session).update({"expires_at": datetime.now() - timedelta(seconds=1)})
    db.commit()
    db.close()
    assert client.get("/api/auth/me").status_code == 401
