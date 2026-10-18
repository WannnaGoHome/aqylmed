from tests.conftest import PASSWORD, TEXT_PAYLOAD, auth_headers, make_user


def test_login_ok_and_me(client):
    make_user()
    headers = auth_headers(client)
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200 and me.json()["email"] == "doc@clinic.kz"
    assert "hashed_password" not in me.text


def test_wrong_password_and_unknown_user_same_message(client):
    make_user()
    a = client.post("/api/auth/login", json={"email": "doc@clinic.kz", "password": "nope"})
    b = client.post("/api/auth/login", json={"email": "ghost@clinic.kz", "password": "nope"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_lockout_after_failed_attempts(client):
    make_user()
    for _ in range(3):
        client.post("/api/auth/login", json={"email": "doc@clinic.kz", "password": "bad"})
    locked = client.post("/api/auth/login", json={"email": "doc@clinic.kz", "password": PASSWORD})
    assert locked.status_code == 429


def test_inactive_user_cannot_login(client):
    make_user(active=False)
    r = client.post("/api/auth/login", json={"email": "doc@clinic.kz", "password": PASSWORD})
    assert r.status_code == 401


def test_endpoints_require_token(client):
    assert client.get("/api/consultations").status_code == 401
    assert client.post("/api/consultations/text", json=TEXT_PAYLOAD).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_deactivated_user_token_stops_working(client):
    user = make_user()
    headers = auth_headers(client)
    from app.core.database import SessionLocal
    from app.models import User
    with SessionLocal() as db:
        db.get(User, user.id).is_active = False
        db.commit()
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_doctor_cannot_use_admin_api(client, doctor):
    assert client.get("/api/admin/users", headers=doctor).status_code == 403
    assert client.get("/api/admin/audit", headers=doctor).status_code == 403


def test_change_password(client, doctor):
    bad = client.post("/api/auth/change-password", headers=doctor,
                      json={"current_password": PASSWORD, "new_password": "short"})
    assert bad.status_code == 400
    ok = client.post("/api/auth/change-password", headers=doctor,
                     json={"current_password": PASSWORD, "new_password": "An0ther-long-pass"})
    assert ok.status_code == 204
    assert client.post("/api/auth/login", json={"email": "doc@clinic.kz", "password": "An0ther-long-pass"}).status_code == 200
