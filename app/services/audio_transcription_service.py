import json
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings
from app.core.errors import ConfigurationError
from app.core.retry import call_with_retries
from app.schemas.diarization_segment import DiarizationSegment
from app.schemas.transcript_segment import SpeakerTranscriptSegment, TranscriptSegment
from app.services.audio_utils import probe_duration, slice_audio


@dataclass
class STTResult:
    text: str
    segments: list[TranscriptSegment]
    raw_json: str
    duration_seconds: float
    provider: str
    model: str


@dataclass
class PerTurnResult:
    segments: list[SpeakerTranscriptSegment]
    text: str
    raw_json: str
    billed_seconds: float
    provider: str
    model: str


class SpeechToTextProvider(ABC):
    name: str
    model: str
    # Отдают ли модель временные метки сегментов (нужны, чтобы сопоставить текст с диаризацией).
    supports_segments: bool = True

    @abstractmethod
    def _transcribe_once(self, path: Path) -> STTResult: ...

    def transcribe(self, path: str | Path) -> STTResult:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")
        result = call_with_retries(
            lambda: self._transcribe_once(path),
            attempts=settings.llm_max_attempts,
            label=f"{self.name}:{self.model} transcription",
        )
        if not result.duration_seconds:
            result.duration_seconds = probe_duration(path) or (
                result.segments[-1].end if result.segments else 0.0
            )
        return result


def _segments_from_raw(raw: dict) -> list[TranscriptSegment]:
    segments = []
    for segment in raw.get("segments") or []:
        segments.append(
            TranscriptSegment(
                start=float(segment.get("start", 0)),
                end=float(segment.get("end", 0)),
                text=(segment.get("text") or "").strip(),
            )
        )
    return segments


class GroqWhisperProvider(SpeechToTextProvider):
    name = "groq"
    supports_segments = True

    def __init__(self, model: str | None = None, language: str | None = None, api_key: str | None = None):
        key = api_key or settings.groq_api_key
        if not key:
            raise ConfigurationError("GROQ_API_KEY не задан в .env")
        from groq import Groq

        self.client = Groq(api_key=key)
        self.model = model or settings.groq_stt_model
        self.language = settings.groq_stt_language if language is None else language

    def _transcribe_once(self, path: Path) -> STTResult:
        kwargs: dict = dict(
            model=self.model,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
            temperature=0.0,
        )
        if self.language:  # пустая строка = автоопределение языка (казахский/смешанная речь)
            kwargs["language"] = self.language
        with path.open("rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(file=audio_file, **kwargs)

        raw = transcription.model_dump()
        return STTResult(
            text=transcription.text,
            segments=_segments_from_raw(raw),
            raw_json=json.dumps(raw, ensure_ascii=False, indent=2, default=str),
            duration_seconds=float(raw.get("duration") or 0.0),
            provider=self.name,
            model=self.model,
        )


class OpenAITranscribeProvider(SpeechToTextProvider):
    """whisper-1 отдаёт сегменты с метками; gpt-4o-*-transcribe — только текст."""

    name = "openai"

    def __init__(self, model: str | None = None, language: str | None = None, api_key: str | None = None):
        key = api_key or settings.openai_api_key
        if not key:
            raise ConfigurationError("OPENAI_API_KEY не задан в .env")
        from openai import OpenAI

        self.client = OpenAI(api_key=key)
        self.model = model or settings.openai_stt_model
        self.language = settings.openai_stt_language if language is None else language
        self.supports_segments = self.model == "whisper-1"

    def _transcribe_once(self, path: Path) -> STTResult:
        kwargs: dict = dict(model=self.model)
        if self.language:
            kwargs["language"] = self.language
        if self.supports_segments:
            kwargs.update(response_format="verbose_json", timestamp_granularities=["segment"])
        else:
            kwargs.update(response_format="json")
        with path.open("rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(file=audio_file, **kwargs)

        raw = transcription.model_dump()
        return STTResult(
            text=transcription.text,
            segments=_segments_from_raw(raw),
            raw_json=json.dumps(raw, ensure_ascii=False, indent=2, default=str),
            duration_seconds=float(raw.get("duration") or 0.0),
            provider=self.name,
            model=self.model,
        )


def build_stt_provider(provider: str | None = None, model: str | None = None) -> SpeechToTextProvider:
    provider = (provider or settings.stt_provider).lower()
    if provider == "groq":
        return GroqWhisperProvider(model=model)
    if provider == "openai":
        return OpenAITranscribeProvider(model=model)
    raise ConfigurationError(f"Неизвестный STT_PROVIDER: {provider} (допустимо: groq, openai)")


class AudioTranscriptionService:
    """Фасад над выбранным провайдером распознавания речи."""

    def __init__(self, provider: SpeechToTextProvider | None = None):
        self.provider = provider or build_stt_provider()

    @property
    def supports_segments(self) -> bool:
        return self.provider.supports_segments

    @property
    def provider_name(self) -> str:
        return self.provider.name

    @property
    def model(self) -> str:
        return self.provider.model

    def transcribe_audio(self, audio_path: str) -> STTResult:
        return self.provider.transcribe(audio_path)

    def transcribe_turns(
        self,
        audio_path: str,
        turns: list[DiarizationSegment],
        min_turn_seconds: float = 0.4,
    ) -> PerTurnResult:
        """Для моделей без временных меток: режем запись по репликам диаризации и распознаём каждую."""
        segments: list[SpeakerTranscriptSegment] = []
        raws: list[dict] = []
        billed = 0.0
        with tempfile.TemporaryDirectory() as tmp:
            for index, turn in enumerate(turns):
                if turn.end - turn.start < min_turn_seconds:
                    continue
                chunk = slice_audio(audio_path, turn.start, turn.end, Path(tmp) / f"turn_{index}.flac")
                result = self.provider.transcribe(chunk)
                billed += result.duration_seconds
                raws.append({"start": turn.start, "end": turn.end, "speaker": turn.speaker,
                             "text": result.text})
                text = result.text.strip()
                if text:
                    segments.append(
                        SpeakerTranscriptSegment(
                            start=turn.start, end=turn.end, speaker=turn.speaker, text=text
                        )
                    )
        return PerTurnResult(
            segments=segments,
            text=" ".join(s.text for s in segments),
            raw_json=json.dumps(raws, ensure_ascii=False, indent=2),
            billed_seconds=billed,
            provider=self.provider.name,
            model=self.provider.model,
        )
