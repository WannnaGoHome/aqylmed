"""Режимы аудио-конвейера: без диаризации и с STT без временных меток."""
import numpy as np
import pytest
import soundfile as sf

from app.core.database import SessionLocal
from app.models import Consultation, UsageRecord
from app.schemas.diarization_segment import DiarizationSegment
from app.services.audio_transcription_service import (
    AudioTranscriptionService, OpenAITranscribeProvider, STTResult, SpeechToTextProvider,
)
from app.services.consultation_service import ConsultationService
from tests.conftest import FakeAI, FakeSTT


@pytest.fixture
def audio_file(tmp_path):
    path = tmp_path / "a.flac"
    sf.write(str(path), (np.random.default_rng(1).standard_normal(16000 * 6) * 0.05).astype("float32"), 16000)
    return str(path)


def run(audio_file, **services):
    with SessionLocal() as db:
        svc = ConsultationService(db, ai_service=FakeAI(), **services)
        c, audio, transcript, doc, memo = svc.process_audio_consultation("P", "D", "2026-10-18", audio_file)
        return c.status, transcript.role_separated_text, doc.complaints, c.id


def test_pipeline_without_diarization(audio_file):
    status, dialogue, complaints, cid = run(audio_file, stt_service=FakeSTT(), diarization_service=None,
                                            diarization_resolved=True)
    assert status == "draft_created" and dialogue.startswith("Врач:") and complaints == "Кашель"


class TextOnlyProvider(SpeechToTextProvider):
    """Как gpt-4o-transcribe: текст есть, меток времени нет."""
    name, model, supports_segments = "fake", "gpt-4o-transcribe", False

    def __init__(self):
        self.chunks = 0

    def _transcribe_once(self, path):
        self.chunks += 1
        return STTResult(f"реплика {self.chunks}", [], "{}", 2.0, "fake", self.model)


def test_text_only_model_is_transcribed_per_diarized_turn(audio_file):
    class Diar:
        def diarize(self, path):
            return [DiarizationSegment(start=0, end=2, speaker="S0"),
                    DiarizationSegment(start=2, end=2.1, speaker="S1"),  # слишком короткая — пропускаем
                    DiarizationSegment(start=3, end=5, speaker="S1")]
    provider = TextOnlyProvider()
    status, _, _, cid = run(audio_file, stt_service=AudioTranscriptionService(provider), diarization_service=Diar())
    assert status == "draft_created" and provider.chunks == 2
    with SessionLocal() as db:
        stt = db.query(UsageRecord).filter_by(consultation_id=cid, kind="stt").one()
        assert stt.model == "gpt-4o-transcribe" and stt.audio_seconds == 4.0
        assert stt.cost_usd == pytest.approx(4 / 60 * 0.006)


def test_text_only_model_without_diarization_uses_whole_text(audio_file):
    provider = TextOnlyProvider()
    status, *_ = run(audio_file, stt_service=AudioTranscriptionService(provider),
                     diarization_service=None, diarization_resolved=True)
    assert status == "draft_created" and provider.chunks == 1


def test_silence_gives_clear_failure(audio_file):
    class Silent(FakeSTT):
        def transcribe_audio(self, path):
            r = super().transcribe_audio(path)
            r.text, r.segments = "  ", []
            return r
    with SessionLocal() as db:
        svc = ConsultationService(db, ai_service=FakeAI(), stt_service=Silent(), diarization_service=None,
                                  diarization_resolved=True)
        with pytest.raises(Exception, match="не удалось распознать речь"):
            svc.process_audio_consultation("P", "D", "d", audio_file)
        c = db.query(Consultation).one()
        assert c.status == "failed" and "не удалось распознать речь" in c.error_message


def test_openai_provider_modes():
    from app.core.errors import ConfigurationError
    with pytest.raises(ConfigurationError):
        OpenAITranscribeProvider(model="whisper-1", api_key=None)
    assert OpenAITranscribeProvider(model="whisper-1", api_key="k").supports_segments is True
    assert OpenAITranscribeProvider(model="gpt-4o-transcribe", api_key="k").supports_segments is False
