from tests.conftest import PASSWORD, TEXT_PAYLOAD, auth_headers, make_user
import re

from app.core.config import settings


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


def test_email_two_factor_login(client, monkeypatch):
    make_user()
    sent = []
    monkeypatch.setattr(settings, "two_factor_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "mail.test")
    monkeypatch.setattr(settings, "smtp_from_email", "noreply@test.invalid")
    monkeypatch.setattr("app.api.auth.send_email", lambda **kwargs: sent.append(kwargs))
    challenge = client.post("/api/auth/login", json={"email": "doc@clinic.kz", "password": PASSWORD})
    assert challenge.status_code == 200
    data = challenge.json()
    assert data["requires_2fa"] and not data["access_token"] and len(sent) == 1
    code = re.search(r"\b\d{6}\b", sent[0]["body"]).group()
    wrong_code = "000001" if code != "000001" else "000002"
    invalid = client.post("/api/auth/verify-login", json={"challenge_id": data["challenge_id"], "code": wrong_code})
    assert invalid.status_code == 401
    verified = client.post("/api/auth/verify-login", json={"challenge_id": data["challenge_id"], "code": code})
    assert verified.status_code == 200 and verified.json()["access_token"]
    replay = client.post("/api/auth/verify-login", json={"challenge_id": data["challenge_id"], "code": code})
    assert replay.status_code == 401


def test_password_reset_is_one_time(client, monkeypatch):
    make_user()
    sent = []
    monkeypatch.setattr("app.api.auth.send_email", lambda **kwargs: sent.append(kwargs))
    response = client.post("/api/auth/password-reset/request", json={"email": "doc@clinic.kz"})
    assert response.status_code == 200
    token = re.search(r"[?&]token=([A-Za-z0-9_-]+)", sent[0]["body"]).group(1)
    payload = {"token": token, "new_password": "An0ther-long-pass"}
    assert client.post("/api/auth/password-reset/confirm", json=payload).status_code == 204
    assert client.post("/api/auth/password-reset/confirm", json=payload).status_code == 400
    login = client.post("/api/auth/login", json={"email": "doc@clinic.kz", "password": payload["new_password"]})
    assert login.status_code == 200


def test_admin_created_user_must_verify_email_when_enabled(client, admin, monkeypatch):
    sent = []
    monkeypatch.setattr(settings, "email_verification_required", True)
    monkeypatch.setattr(settings, "smtp_host", "mail.test")
    monkeypatch.setattr(settings, "smtp_from_email", "noreply@test.invalid")
    monkeypatch.setattr("app.api.admin.send_email", lambda **kwargs: sent.append(kwargs))
    created = client.post("/api/admin/users", headers=admin, json={
        "email": "new@clinic.kz", "full_name": "Новый врач",
        "password": "An0ther-long-pass", "role": "doctor",
    })
    assert created.status_code == 201 and created.json()["email_verified"] is False
    assert client.post("/api/auth/login", json={
        "email": "new@clinic.kz", "password": "An0ther-long-pass",
    }).status_code == 403
    token = re.search(r"token=([A-Za-z0-9_-]+)", sent[0]["body"]).group(1)
    assert client.post("/api/auth/verify-email", params={"token": token}).status_code == 204
    assert client.post("/api/auth/login", json={
        "email": "new@clinic.kz", "password": "An0ther-long-pass",
    }).status_code == 200
