import json
from pathlib import Path

from app.core.database import SessionLocal
from app.models import AuditLog, Consultation, UsageRecord
from tests.conftest import TEXT_PAYLOAD, auth_headers, make_user


def create_text(client, headers):
    r = client.post("/api/consultations/text", json=TEXT_PAYLOAD, headers=headers)
    assert r.status_code == 202, r.text
    return r.json()["id"]


def test_text_flow_creates_draft_with_warnings_and_cost(client, doctor, fakes):
    cid = create_text(client, doctor)
    detail = client.get(f"/api/consultations/{cid}", headers=doctor).json()
    assert detail["status"] == "draft_created" and detail["can_edit"] is True
    assert detail["document"]["complaints"] == "Кашель"
    assert detail["document"]["symptoms_duration"] == "Кашель — 3 дня"
    assert detail["memo"]["memo_text"].startswith("1.")
    # «500 мг» выдумано ИИ — должно быть подсвечено; «38,5°C» есть в диалоге — нет
    warnings = " ".join(detail["document"]["validation_warnings"])
    assert "500 мг" in warnings and "38,5" not in warnings
    assert fakes.ai.output_calls == 1 and fakes.ai.dialogue_calls == 0
    with SessionLocal() as db:
        assert db.query(UsageRecord).filter_by(consultation_id=cid, kind="llm").count() == 1


def test_doctor_sees_only_own_consultations(client, doctor):
    cid = create_text(client, doctor)
    make_user("other@clinic.kz", name="Другой")
    other = auth_headers(client, "other@clinic.kz")
    assert client.get(f"/api/consultations/{cid}", headers=other).status_code == 404
    assert client.get(f"/api/consultations/{cid}/export", headers=other).status_code == 404
    assert client.put(f"/api/consultations/{cid}/document", json={"complaints": "x"}, headers=other).status_code == 404
    assert client.get("/api/consultations", headers=other).json()["total"] == 0
    assert client.get("/api/consultations", headers=doctor).json()["total"] == 1


def test_admin_sees_all(client, doctor, admin):
    create_text(client, doctor)
    assert client.get("/api/consultations", headers=admin).json()["total"] == 1


def test_edit_confirm_lock_reopen(client, doctor):
    cid = create_text(client, doctor)
    edited = client.put(f"/api/consultations/{cid}/document", headers=doctor,
                        json={"diagnosis": "ОРВИ", "missing_information": ["a", " ", "b"]})
    assert edited.status_code == 200
    doc = edited.json()["document"]
    assert doc["diagnosis"] == "ОРВИ" and doc["missing_information"] == ["a", "b"] and doc["edited_at"]
    assert doc["complaints"] == "Кашель"  # неуказанные поля не затираются

    confirmed = client.post(f"/api/consultations/{cid}/confirm", headers=doctor).json()
    assert confirmed["status"] == "confirmed" and confirmed["confirmed_by"] == "Петрова А.К."
    # после подтверждения правки и перегенерация запрещены
    assert client.put(f"/api/consultations/{cid}/document", json={"diagnosis": "x"}, headers=doctor).status_code == 409
    assert client.put(f"/api/consultations/{cid}/memo", json={"memo_text": "x"}, headers=doctor).status_code == 409
    assert client.post(f"/api/consultations/{cid}/regenerate", json={}, headers=doctor).status_code == 409

    reopened = client.post(f"/api/consultations/{cid}/reopen", headers=doctor).json()
    assert reopened["status"] == "draft_created" and reopened["confirmed_at"] is None


def test_ai_original_is_kept_after_doctor_edit(client, doctor):
    cid = create_text(client, doctor)
    client.put(f"/api/consultations/{cid}/document", json={"diagnosis": "ОРВИ"}, headers=doctor)
    with SessionLocal() as db:
        original = json.loads(db.get(Consultation, cid).medical_document.ai_original_json)
    assert original["diagnosis"] == "Точный диагноз не указан врачом"


def test_regenerate_requires_overwrite_confirmation(client, doctor, fakes):
    cid = create_text(client, doctor)
    client.put(f"/api/consultations/{cid}/dialogue", headers=doctor,
               json={"dialogue_text": "Врач: Исправленный диалог\nПациент: Да"})
    client.put(f"/api/consultations/{cid}/document", json={"diagnosis": "моя правка"}, headers=doctor)

    blocked = client.post(f"/api/consultations/{cid}/regenerate", json={}, headers=doctor)
    assert blocked.status_code == 409 and blocked.json()["detail"]["code"] == "edits_would_be_lost"

    ok = client.post(f"/api/consultations/{cid}/regenerate", json={"confirm_overwrite": True}, headers=doctor)
    assert ok.status_code == 202
    assert fakes.ai.last_dialogue == "Врач: Исправленный диалог\nПациент: Да"
    detail = client.get(f"/api/consultations/{cid}", headers=doctor).json()
    assert detail["document"]["diagnosis"] == "Точный диагноз не указан врачом"
    assert detail["document"]["edited_at"] is None


def test_swap_roles(client, doctor):
    cid = create_text(client, doctor)
    r = client.post(f"/api/consultations/{cid}/swap-roles", headers=doctor).json()
    assert r["dialogue_text"].startswith("Пациент: Что беспокоит?")
    assert "\nВрач: Кашель три дня" in r["dialogue_text"]


def test_failure_is_reported_without_leaking_internals_and_can_retry(client, doctor, fakes):
    fakes.ai.fail_next = True
    cid = create_text(client, doctor)
    status = client.get(f"/api/consultations/{cid}/status", headers=doctor).json()
    assert status["status"] == "failed"
    assert "secret-internal-detail" not in status["error_message"]
    retry = client.post(f"/api/consultations/{cid}/regenerate", json={}, headers=doctor)
    assert retry.status_code == 202
    assert client.get(f"/api/consultations/{cid}/status", headers=doctor).json()["status"] == "draft_created"


def test_validation_errors(client, doctor):
    assert client.post("/api/consultations/text", headers=doctor,
                       json={**TEXT_PAYLOAD, "dialogue_text": "коротко"}).status_code == 422
    assert client.get("/api/consultations/9999", headers=doctor).status_code == 404


def test_export_docx_and_txt(client, doctor):
    cid = create_text(client, doctor)
    docx = client.get(f"/api/consultations/{cid}/export?format=docx", headers=doctor)
    assert docx.status_code == 200 and docx.content[:2] == b"PK"
    from docx import Document
    import io
    text = "\n".join(p.text for p in Document(io.BytesIO(docx.content)).paragraphs)
    assert "ЧЕРНОВИК" in text and "Иванов И.И." in text and "Кашель" in text
    txt = client.get(f"/api/consultations/{cid}/export?format=txt", headers=doctor)
    assert "ЧЕРНОВИК" in txt.text
    client.post(f"/api/consultations/{cid}/confirm", headers=doctor)
    assert "Подтверждено врачом: Петрова А.К." in client.get(f"/api/consultations/{cid}/export?format=txt", headers=doctor).text
    assert client.get(f"/api/consultations/{cid}/export?format=exe", headers=doctor).status_code == 422


def test_audio_flow_end_to_end(client, doctor, fakes, wav_bytes):
    r = client.post("/api/consultations/audio", headers=doctor,
                    data={"patient_name": "Сидоров", "consultation_date": "2026-10-18", "consent_confirmed": "true"},
                    files={"file": ("visit.wav", wav_bytes, "audio/wav")})
    assert r.status_code == 202, r.text
    cid = r.json()["id"]
    detail = client.get(f"/api/consultations/{cid}", headers=doctor).json()
    assert detail["status"] == "draft_created" and detail["source"] == "audio"
    assert detail["dialogue_text"].startswith("Врач:")
    assert "лод -> температура" in detail["transcript_notes"]
    assert detail["audio"]["available"] and detail["audio"]["duration_seconds"] in (1, 2)
    assert fakes.stt.calls == 1 and fakes.ai.dialogue_calls == 1 and fakes.ai.output_calls == 1
    with SessionLocal() as db:
        kinds = {u.kind: u for u in db.query(UsageRecord).filter_by(consultation_id=cid)}
        # 120 c * 0.00185 $/мин = 0.0037
        assert abs(kinds["stt"].cost_usd - 0.0037) < 1e-9
        assert kinds["llm"].cost_usd > 0

    audio = client.get(f"/api/consultations/{cid}/audio", headers=doctor)
    assert audio.status_code == 200 and audio.headers["content-type"] == "audio/flac"
    path = Path(__import__("app.core.config", fromlist=["settings"]).settings.upload_dir)
    assert not list((path / "_incoming").glob("*"))  # временные файлы убраны

    assert client.delete(f"/api/consultations/{cid}/audio", headers=doctor).status_code == 204
    assert client.get(f"/api/consultations/{cid}/audio", headers=doctor).status_code == 404
    assert client.get(f"/api/consultations/{cid}", headers=doctor).json()["audio"]["available"] is False


def test_audio_upload_validation(client, doctor, wav_bytes):
    data = {"patient_name": "X", "consultation_date": "2026-10-18", "consent_confirmed": "true"}
    bad_ext = client.post("/api/consultations/audio", headers=doctor, data=data,
                          files={"file": ("virus.exe", b"MZ...", "application/octet-stream")})
    assert bad_ext.status_code == 415
    empty = client.post("/api/consultations/audio", headers=doctor, data=data,
                        files={"file": ("a.wav", b"", "audio/wav")})
    assert empty.status_code == 400
    garbage = client.post("/api/consultations/audio", headers=doctor, data=data,
                          files={"file": ("a.mp3", b"this is not audio at all", "audio/mpeg")})
    assert garbage.status_code == 422
    traversal = client.post("/api/consultations/audio", headers=doctor, data=data,
                            files={"file": ("../../etc/passwd.wav", wav_bytes, "audio/wav")})
    assert traversal.status_code == 202  # имя игнорируется, файл хранится под uuid


def test_upload_size_limit(client, doctor, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    r = client.post("/api/consultations/audio", headers=doctor,
                    data={"patient_name": "X", "consultation_date": "d", "consent_confirmed": "true"},
                    files={"file": ("big.wav", b"\0" * (1024 * 1024 + 10), "audio/wav")})
    assert r.status_code == 413


def test_budget_limit_blocks_new_processing(client, doctor, monkeypatch):
    from app.core.config import settings
    cid = create_text(client, doctor)  # стоимость > 0 уже записана
    monkeypatch.setattr(settings, "monthly_api_budget_usd", 0.0001)
    r = client.post("/api/consultations/text", json=TEXT_PAYLOAD, headers=doctor)
    assert r.status_code == 429 and "лимит" in r.json()["detail"]
    assert client.post(f"/api/consultations/{cid}/regenerate", json={}, headers=doctor).status_code == 429


def test_audit_trail_has_no_patient_data(client, doctor, admin):
    cid = create_text(client, doctor)
    client.get(f"/api/consultations/{cid}", headers=doctor)
    client.get(f"/api/consultations/{cid}/export", headers=doctor)
    client.post(f"/api/consultations/{cid}/confirm", headers=doctor)
    log = client.get("/api/admin/audit?limit=200", headers=admin).json()
    actions = {i["action"] for i in log["items"]}
    assert {"auth.login", "consultation.create", "consultation.view", "consultation.export",
            "consultation.confirm"} <= actions
    assert "Иванов" not in json.dumps(log, ensure_ascii=False)
    filtered = client.get(f"/api/admin/audit?entity_id={cid}", headers=admin).json()
    assert filtered["total"] >= 4


def test_admin_delete_cascades_and_keeps_usage(client, doctor, admin):
    cid = create_text(client, doctor)
    assert client.delete(f"/api/consultations/{cid}", headers=doctor).status_code == 403
    assert client.delete(f"/api/consultations/{cid}", headers=admin).status_code == 204
    with SessionLocal() as db:
        assert db.query(Consultation).count() == 0
        assert db.query(UsageRecord).count() == 1  # учёт расходов сохраняется, связь обнулена
        assert db.query(UsageRecord).first().consultation_id is None
        assert db.query(AuditLog).filter_by(action="consultation.delete").count() == 1


def test_audio_requires_patient_consent(client, doctor, wav_bytes):
    r = client.post("/api/consultations/audio", headers=doctor,
                    data={"patient_name": "A", "consultation_date": "d", "consent_confirmed": "false"},
                    files={"file": ("a.wav", wav_bytes, "audio/wav")})
    assert r.status_code == 400 and "согласие" in r.json()["detail"]
    r = client.post("/api/consultations/audio", headers=doctor,
                    data={"patient_name": "A", "consultation_date": "d"},
                    files={"file": ("a.wav", wav_bytes, "audio/wav")})
    assert r.status_code == 422


def test_search_is_case_insensitive_for_cyrillic(client, doctor):
    import pytest
    from app.core.database import engine
    if engine.dialect.name == "sqlite":
        pytest.skip("lower() в SQLite не работает с кириллицей; боевая БД — PostgreSQL")
    create_text(client, doctor)
    assert client.get("/api/consultations?q=иванов", headers=doctor).json()["total"] == 1
    assert client.get("/api/consultations?q=ПЕТРОВА", headers=doctor).json()["total"] == 1  # поиск идёт и по ФИО врача
    assert client.get("/api/consultations?q=нет такого", headers=doctor).json()["total"] == 0
