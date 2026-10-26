import re
from datetime import timedelta

import pytest

from app.core.database import SessionLocal
from app.core.timeutils import utcnow
from app.models import User
from app.models.medical_catalog import Icd10Code
from tests.conftest import TEXT_PAYLOAD, PASSWORD, make_user, auth_headers


def test_confirmation_requires_icd_even_without_catalog(client, doctor):
    cid = client.post('/api/consultations/text', headers=doctor, json=TEXT_PAYLOAD).json()['id']
    assert client.post(f'/api/consultations/{cid}/confirm', headers=doctor).status_code == 422
    assert client.put(f'/api/consultations/{cid}/document', headers=doctor,
                      json={'diagnosis': '', 'diagnosis_code': 'X12'}).status_code == 422
    assert client.post(f'/api/consultations/{cid}/confirm', headers=doctor).status_code == 422


def test_catalog_import_permissions_idempotency_and_atomicity(client, doctor, admin):
    entries = [{'name_ru': 'Терапевт', 'name_en': 'Physician'}]
    assert client.put('/api/catalog/specialties', headers=doctor, json=entries).status_code == 403
    for _ in range(2):
        assert client.put('/api/catalog/specialties', headers=admin, json=entries).status_code == 200
    assert len(client.get('/api/catalog/specialties', headers=doctor).json()) == 1
    assert client.put('/api/catalog/specialties', headers=admin, json=[
        {'name_ru': 'Хирург'}, {'name_ru': '   '},
    ]).status_code == 422
    assert len(client.get('/api/catalog/specialties', headers=doctor).json()) == 1
    assert client.put('/api/catalog/icd10', headers=admin, json=[
        {'code': 'J06.9', 'name_ru': 'Первое название'},
        {'code': 'J06.9', 'name_ru': 'Обновлённое название'},
    ]).status_code == 200
    assert client.get('/api/catalog/icd10?q=J06&locale=en', headers=doctor).json()[0]['name'] == 'Обновлённое название'


@pytest.mark.parametrize('locale', ['ru', 'kk', 'en'])
@pytest.mark.parametrize('kind', ['initial', 'examination', 'discharge'])
def test_template_type_language_and_snapshot(client, doctor, admin, fakes, locale, kind):
    specialty = client.post('/api/catalog/specialties', headers=admin,
                            json={'name_ru': 'Терапевт'}).json()['id']
    uid = client.get('/api/auth/me', headers=doctor).json()['id']
    assert client.patch(f'/api/admin/users/{uid}', headers=admin,
                        json={'specialty_id': specialty}).status_code == 200
    assert client.patch('/api/auth/preferences', headers=doctor, json={'locale': locale}).status_code == 200
    payload = {'locale': locale, 'document_type': kind, 'fields': {'complaints': f'Custom {locale} {kind}'}}
    path = f'/api/catalog/specialties/{specialty}/template'
    assert client.put(path, headers=admin, json=payload).status_code == 200
    response = client.post('/api/consultations/text', headers=doctor,
                           json={**TEXT_PAYLOAD, 'document_type': kind})
    assert response.status_code == 202
    cid = response.json()['id']
    result = client.get(f'/api/consultations/{cid}', headers=admin).json()
    assert result['template_fields'] == payload['fields']
    assert result['document_type'] == kind and result['output_locale'] == locale
    assert fakes.ai.last_document_type == kind
    client.put(path, headers=admin, json={**payload, 'fields': {'complaints': 'Changed'}})
    client.patch(f'/api/admin/users/{uid}', headers=admin, json={'specialty_id': None})
    assert client.get(f'/api/consultations/{cid}', headers=doctor).json()['template_fields'] == payload['fields']
    exported = client.get(f'/api/consultations/{cid}/export?format=txt', headers=admin)
    assert payload['fields']['complaints'] in exported.text
    assert 'Changed' not in exported.text


def test_audio_detected_locale_overrides_user_locale(client, doctor, fakes, wav_bytes):
    generate = fakes.ai.generate_consultation_output
    def kazakh(*args, **kwargs):
        output, usage = generate(*args, **kwargs)
        output.output_locale = 'kk'
        return output, usage
    fakes.ai.generate_consultation_output = kazakh
    response = client.post('/api/consultations/audio', headers=doctor,
        data={'patient_name': 'Test', 'consultation_date': '2026-10-22',
              'consent_confirmed': 'true', 'document_type': 'examination'},
        files={'file': ('visit.wav', wav_bytes, 'audio/wav')})
    assert response.status_code == 202
    cid = response.json()['id']
    assert client.get(f'/api/consultations/{cid}', headers=doctor).json()['output_locale'] == 'kk'
    assert 'Медициналық қорытынды'.upper() in client.get(
        f'/api/consultations/{cid}/export?format=txt', headers=doctor).text


def test_reset_revokes_sessions_and_expired_links_fail(client, monkeypatch):
    from app.api import auth
    auth._reset_limiter._failures.clear()
    user = make_user()
    headers = auth_headers(client)
    sent = []
    monkeypatch.setattr(auth, 'send_email', lambda **kwargs: sent.append(kwargs))
    client.post('/api/auth/password-reset/request', json={'email': user.email})
    token = re.search(r'token=([A-Za-z0-9_-]+)', sent[-1]['body']).group(1)
    with SessionLocal() as db:
        db.get(User, user.id).password_reset_expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    payload = {'token': token, 'new_password': 'New-password-1234'}
    assert client.post('/api/auth/password-reset/confirm', json=payload).status_code == 400
    client.post('/api/auth/password-reset/request', json={'email': user.email})
    payload['token'] = re.search(r'token=([A-Za-z0-9_-]+)', sent[-1]['body']).group(1)
    assert client.post('/api/auth/password-reset/confirm', json=payload).status_code == 204
    assert client.get('/api/auth/me', headers=headers).status_code == 401


def test_expired_otp_cannot_login(client, monkeypatch):
    from app.api import auth
    from app.core.config import settings
    auth._otp_limiter._failures.clear()
    user = make_user()
    sent = []
    monkeypatch.setattr(settings, 'two_factor_enabled', True)
    monkeypatch.setattr(settings, 'smtp_host', 'test.invalid')
    monkeypatch.setattr(settings, 'smtp_from_email', 'test@example.invalid')
    monkeypatch.setattr(auth, 'send_email', lambda **kwargs: sent.append(kwargs))
    result = client.post('/api/auth/login', json={'email': user.email, 'password': PASSWORD}).json()
    code = re.search(r'\b\d{6}\b', sent[-1]['body']).group()
    with SessionLocal() as db:
        db.get(User, user.id).two_factor_expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.post('/api/auth/verify-login', json={
        'challenge_id': result['challenge_id'], 'code': code,
    }).status_code == 401


def test_password_notification_failure_does_not_report_password_change_failure(client, doctor, monkeypatch):
    from app.api import auth
    from app.core.config import settings
    from app.services.email_service import EmailDeliveryError
    monkeypatch.setattr(settings, 'email_notifications_enabled', True)
    monkeypatch.setattr(settings, 'smtp_host', 'test.invalid')
    monkeypatch.setattr(settings, 'smtp_from_email', 'test@example.invalid')
    def fail(**kwargs):
        raise EmailDeliveryError('SMTP temporarily unavailable')
    monkeypatch.setattr(auth, 'send_email', fail)
    result = client.post('/api/auth/change-password', headers=doctor,
                         json={'current_password': PASSWORD, 'new_password': 'Changed-password-123'})
    assert result.status_code == 204
    assert client.get('/api/auth/me', headers=doctor).status_code == 401
    assert client.post('/api/auth/login', json={
        'email': 'doc@clinic.kz', 'password': 'Changed-password-123',
    }).status_code == 200


def test_system_notifications_success_and_failure(client, doctor, fakes, monkeypatch):
    from app.core.config import settings
    sent = []
    monkeypatch.setattr(settings, 'email_notifications_enabled', True)
    monkeypatch.setattr('app.services.consultation_service.send_email', lambda **kw: sent.append(kw))
    client.post('/api/consultations/text', headers=doctor, json=TEXT_PAYLOAD)
    fakes.ai.fail_next = True
    client.post('/api/consultations/text', headers=doctor, json=TEXT_PAYLOAD)
    assert len(sent) == 2
    assert 'готов' in sent[0]['subject'] and 'Ошибка' in sent[1]['subject']
    assert all(TEXT_PAYLOAD['patient_name'] not in item['body'] for item in sent)
