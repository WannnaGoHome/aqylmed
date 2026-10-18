"""Демо-сервер интерфейса БЕЗ ключей и без реального ИИ: вместо Gemini/Whisper подставлены заглушки.
Нужен только чтобы посмотреть, как выглядит и работает интерфейс. Тексты заключений — выдуманные заглушки,
никогда не используйте этот режим с реальными пациентами.

    python -m tests.demo_server          # http://127.0.0.1:8765  (врач: doc@demo.kz / Demo-pass-12345)
"""
import time

import uvicorn

from tests.conftest import FakeAI, FakeDiarizer, FakeSTT  # noqa: E402  (задаёт тестовое окружение)

from app.api.deps import get_runner
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.main import app
from app.models import User
from app.services.consultation_service import ConsultationService
from app.services.runner import ProcessingRunner

DELAY = 1.5


class SlowAI(FakeAI):
    def process_dialogue(self, t):
        time.sleep(DELAY)
        return super().process_dialogue(t)

    def generate_consultation_output(self, d):
        time.sleep(DELAY)
        return super().generate_consultation_output(d)


class SlowSTT(FakeSTT):
    def transcribe_audio(self, p):
        time.sleep(DELAY)
        return super().transcribe_audio(p)


class SlowDiar(FakeDiarizer):
    def diarize(self, p):
        time.sleep(DELAY)
        return super().diarize(p)


if __name__ == "__main__":
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add_all([
            User(email="doc@demo.kz", full_name="Петрова А. К.", role="doctor", hashed_password=hash_password("Demo-pass-12345")),
            User(email="admin@demo.kz", full_name="Администратор", role="admin", hashed_password=hash_password("Demo-pass-12345")),
        ])
        db.commit()
    ai, stt, diar = SlowAI(), SlowSTT(), SlowDiar()
    runner = ProcessingRunner(service_factory=lambda db: ConsultationService(
        db, ai_service=ai, stt_service=stt, diarization_service=diar))
    app.dependency_overrides[get_runner] = lambda: runner
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
