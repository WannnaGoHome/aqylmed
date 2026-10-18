"""Ленивое создание тяжёлых сервисов: клиенты API и модель pyannote создаются один раз и только при необходимости."""
import threading
from functools import lru_cache

from app.core.config import settings

_lock = threading.Lock()


@lru_cache(maxsize=1)
def get_ai_service():
    from app.services.gemini_ai_service import GeminiAIService

    return GeminiAIService()


@lru_cache(maxsize=1)
def get_stt_service():
    from app.services.audio_transcription_service import AudioTranscriptionService

    return AudioTranscriptionService()


_diarizer = None


def get_diarization_service():
    """None, если диаризация выключена: тогда роли определяет языковая модель по смыслу реплик."""
    global _diarizer
    if not settings.diarization_enabled:
        return None
    with _lock:
        if _diarizer is None:
            from app.services.audio_diarization_service import AudioDiarizationService

            _diarizer = AudioDiarizationService()
        return _diarizer
