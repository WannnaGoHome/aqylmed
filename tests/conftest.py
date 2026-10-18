import os
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="aqyl_tests_")
os.environ.update(
    DATABASE_URL=os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_TMP}/test.db",
    SECRET_KEY="test-secret-key-for-tests-0123456789abcdef",
    UPLOAD_DIR=f"{_TMP}/audio",
    ENVIRONMENT="development",
    GEMINI_API_KEY="", GROQ_API_KEY="", OPENAI_API_KEY="", HF_TOKEN="",
    MONTHLY_API_BUDGET_USD="0", AUDIO_RETENTION_DAYS="30",
    DELETE_AUDIO_AFTER_PROCESSING="false", LOGIN_MAX_ATTEMPTS="3",
)

import numpy as np  # noqa: E402
import pytest  # noqa: E402
import soundfile as sf  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.deps import get_runner, login_limiter  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.schemas.consultation_ai_output import ConsultationAIOutput  # noqa: E402
from app.schemas.dialogue_processing import DialogueProcessingResult  # noqa: E402
from app.schemas.diarization_segment import DiarizationSegment  # noqa: E402
from app.schemas.medical_document import MedicalDocumentDraft  # noqa: E402
from app.schemas.patient_memo import PatientMemoDraft  # noqa: E402
from app.schemas.transcript_segment import TranscriptSegment  # noqa: E402
from app.services.audio_transcription_service import STTResult  # noqa: E402
from app.services.consultation_service import ConsultationService  # noqa: E402
from app.services.gemini_ai_service import LLMUsage  # noqa: E402
from app.services.runner import ProcessingRunner  # noqa: E402

PASSWORD = "Str0ng-pass-123"


class FakeAI:
    provider_name = "fake"

    def __init__(self):
        self.dialogue_calls = 0
        self.output_calls = 0
        self.fail_next = False
        self.last_dialogue = None

    def process_dialogue(self, speaker_transcript):
        self.dialogue_calls += 1
        return DialogueProcessingResult(
            cleaned_text="Здравствуйте. Кашель три дня, температура 38,5.",
            role_separated_text="Врач: Здравствуйте, что беспокоит?\nПациент: Кашель три дня, температура 38,5.",
            speaker_roles={"SPEAKER_00": "doctor", "SPEAKER_01": "patient"},
            uncertain_segments=["неразборчиво на 00:12"], processing_notes=["исправлено: лод -> температура"],
        ), LLMUsage("gemini-3.5-flash", 2000, 400)

    def generate_consultation_output(self, dialogue_text):
        self.output_calls += 1
        self.last_dialogue = dialogue_text
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("boom: secret-internal-detail")
        return ConsultationAIOutput(
            medical_document=MedicalDocumentDraft(
                complaints="Кашель", anamnesis="Болеет 3 дня", symptoms_duration="Кашель — 3 дня",
                examination="Аускультация лёгких", diagnosis="Точный диагноз не указан врачом",
                treatment_plan="Жаропонижающее при температуре выше 38,5°C",
                recommendations="Парацетамол 500 мг при необходимости",  # 500 мг в диалоге нет
                missing_information=["Аллергии не уточнены"],
            ),
            patient_memo=PatientMemoDraft(memo_text="1. Пить больше жидкости\n2. Повторный визит при ухудшении"),
        ), LLMUsage("gemini-3.5-flash", 3000, 800)


class FakeSTT:
    supports_segments = True
    provider_name = "fake"
    model = "whisper-large-v3"

    def __init__(self):
        self.calls = 0

    def transcribe_audio(self, path):
        self.calls += 1
        return STTResult(
            text="Здравствуйте что беспокоит Кашель три дня",
            segments=[TranscriptSegment(start=0.0, end=1.0, text="Здравствуйте, что беспокоит?"),
                      TranscriptSegment(start=1.1, end=2.0, text="Кашель три дня")],
            raw_json="{}", duration_seconds=120.0, provider="fake", model="whisper-large-v3",
        )


class FakeDiarizer:
    def diarize(self, path):
        return [DiarizationSegment(start=0.0, end=1.05, speaker="SPEAKER_00"),
                DiarizationSegment(start=1.05, end=2.0, speaker="SPEAKER_01")]


@pytest.fixture(scope="session", autouse=True)
def _enable_tables():
    yield


@pytest.fixture(autouse=True)
def _clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    login_limiter._failures.clear()
    yield


@pytest.fixture
def fakes():
    return type("Fakes", (), {"ai": FakeAI(), "stt": FakeSTT(), "diar": FakeDiarizer()})()


@pytest.fixture
def client(fakes):
    runner = ProcessingRunner(
        service_factory=lambda db: ConsultationService(
            db, ai_service=fakes.ai, stt_service=fakes.stt, diarization_service=fakes.diar
        )
    )
    app.dependency_overrides[get_runner] = lambda: runner
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(email="doc@clinic.kz", role="doctor", name="Петрова А.К.", active=True) -> User:
    with SessionLocal() as db:
        user = User(email=email, full_name=name, hashed_password=hash_password(PASSWORD), role=role,
                    is_active=active)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def auth_headers(client, email="doc@clinic.kz") -> dict:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def doctor(client):
    make_user()
    return auth_headers(client)


@pytest.fixture
def admin(client):
    make_user("admin@clinic.kz", role="admin", name="Админ")
    return auth_headers(client, "admin@clinic.kz")


@pytest.fixture
def wav_bytes(tmp_path) -> bytes:
    path = tmp_path / "t.wav"
    t = np.linspace(0, 2, 2 * 44100, endpoint=False)
    sf.write(str(path), np.stack([np.sin(2 * np.pi * 220 * t)] * 2, axis=1).astype("float32") * 0.3, 44100)
    return Path(path).read_bytes()


TEXT_PAYLOAD = {
    "patient_name": "Иванов И.И.", "consultation_date": "2026-10-18",
    "dialogue_text": "Врач: Что беспокоит?\nПациент: Кашель три дня, температура 38,5.",
}
