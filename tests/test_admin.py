from tests.conftest import PASSWORD, TEXT_PAYLOAD, make_user


def test_user_management(client, admin):
    r = client.post("/api/admin/users", headers=admin,
                    json={"email": "New@Clinic.kz", "full_name": "Новый Врач", "password": PASSWORD, "role": "doctor"})
    assert r.status_code == 201 and r.json()["email"] == "new@clinic.kz"
    dup = client.post("/api/admin/users", headers=admin,
                      json={"email": "new@clinic.kz", "full_name": "Дубль", "password": PASSWORD})
    assert dup.status_code == 409
    weak = client.post("/api/admin/users", headers=admin,
                       json={"email": "w@clinic.kz", "full_name": "Слабый", "password": "12345678"})
    assert weak.status_code == 422
    badrole = client.post("/api/admin/users", headers=admin,
                          json={"email": "r@clinic.kz", "full_name": "Роль", "password": PASSWORD, "role": "root"})
    assert badrole.status_code == 422
    uid = r.json()["id"]
    assert client.patch(f"/api/admin/users/{uid}", headers=admin, json={"is_active": False}).json()["is_active"] is False
    # отключённый врач больше не входит
    assert client.post("/api/auth/login", json={"email": "new@clinic.kz", "password": PASSWORD}).status_code == 401


def test_cannot_remove_last_admin(client, admin):
    me = client.get("/api/auth/me", headers=admin).json()
    assert client.patch(f"/api/admin/users/{me['id']}", headers=admin, json={"is_active": False}).status_code == 400
    assert client.patch(f"/api/admin/users/{me['id']}", headers=admin, json={"role": "doctor"}).status_code == 400


def test_usage_summary(client, doctor, admin):
    client.post("/api/consultations/text", json=TEXT_PAYLOAD, headers=doctor)
    s = client.get("/api/admin/usage", headers=admin).json()
    # gemini-3.8-flash: 3000 in * 1.5 + 800 out * 9.0 = 0.0117 $
    assert abs(s["total_cost_usd"] - 0.0117) < 1e-6
    assert s["consultations_processed"] == 1 and s["budget_used_percent"] is None
    assert s["by_model"][0]["model"] == "gemini-3.8-flash" and len(s["by_day"]) == 1
    assert client.get("/api/admin/usage?month=2020-01", headers=admin).json()["total_cost_usd"] == 0
    assert client.get("/api/admin/usage?month=bad", headers=admin).status_code == 422


def test_retention_purge(client, doctor, admin, wav_bytes):
    from datetime import timedelta
    from pathlib import Path
    from app.core.database import SessionLocal
    from app.core.timeutils import utcnow
    from app.models import AudioFile

    r = client.post("/api/consultations/audio", headers=doctor,
                    data={"patient_name": "A", "consultation_date": "d", "consent_confirmed": "true"},
                    files={"file": ("a.wav", wav_bytes, "audio/wav")})
    cid = r.json()["id"]
    assert client.post("/api/admin/retention/purge", headers=admin).json()["deleted_files"] == 0  # свежая запись
    with SessionLocal() as db:
        audio = db.query(AudioFile).filter_by(consultation_id=cid).one()
        path = Path(audio.file_path)
        audio.created_at = utcnow() - timedelta(days=31)
        db.commit()
    assert path.exists()
    assert client.post("/api/admin/retention/purge", headers=admin).json()["deleted_files"] == 1
    assert not path.exists()
    assert client.get(f"/api/consultations/{cid}", headers=doctor).json()["audio"]["available"] is False


def test_delete_audio_after_processing(client, doctor, wav_bytes, monkeypatch):
    from pathlib import Path
    from app.core.config import settings
    monkeypatch.setattr(settings, "delete_audio_after_processing", True)
    cid = client.post("/api/consultations/audio", headers=doctor,
                      data={"patient_name": "A", "consultation_date": "d", "consent_confirmed": "true"},
                      files={"file": ("a.wav", wav_bytes, "audio/wav")}).json()["id"]
    d = client.get(f"/api/consultations/{cid}", headers=doctor).json()
    assert d["status"] == "draft_created" and d["audio"]["available"] is False
    assert not any(Path(settings.upload_dir).glob("*.flac"))


def test_security_headers_and_health(client):
    r = client.get("/api/health")
    assert r.json() == {"status": "ok", "database": True}
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "no-store"


def test_bootstrap_admin_and_stuck_recovery(monkeypatch):
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.main import bootstrap
    from app.models import Consultation, User
    monkeypatch.setattr(settings, "bootstrap_admin_email", "boss@clinic.kz")
    monkeypatch.setattr(settings, "bootstrap_admin_password", PASSWORD)
    with SessionLocal() as db:
        db.add(Consultation(patient_name="p", doctor_name="d", consultation_date="x", status="processing"))
        db.commit()
    bootstrap()
    bootstrap()  # идемпотентно
    with SessionLocal() as db:
        assert db.query(User).filter_by(email="boss@clinic.kz", role="admin").count() == 1
        assert db.query(User).count() == 1
        assert db.query(Consultation).one().status == "failed"
