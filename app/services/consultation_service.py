import logging
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import (
    AIResponseError, BudgetExceededError, ConfigurationError, ProcessingError,
)
from app.core.timeutils import utcnow
from app.models.consultation import Consultation, ConsultationSource, ConsultationStatus
from app.repositories.audio_file_repository import AudioFileRepository
from app.repositories.consultation_repository import ConsultationRepository
from app.repositories.medical_document_repository import MedicalDocumentRepository
from app.repositories.patient_memo_repository import PatientMemoRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.schemas.transcript_segment import SpeakerTranscriptSegment
from app.services.audio_utils import AudioError
from app.services.retention_service import AudioRetentionService
from app.services.transcript_alignment_service import (
    UNKNOWN_SPEAKER, TranscriptAlignmentService, build_speaker_transcript,
)
from app.services.usage_service import UsageService
from app.services.validation_service import validate_generated_output

logger = logging.getLogger(__name__)

_ROLE_RE = re.compile(r"(?m)^(\s*)(Врач|Пациент)(\s*:)")
_SWAP = {"Врач": "Пациент", "Пациент": "Врач"}


def swap_roles(text: str) -> str:
    """Меняет местами метки «Врач:» и «Пациент:» (если диаризация перепутала роли)."""
    return _ROLE_RE.sub(lambda m: f"{m.group(1)}{_SWAP[m.group(2)]}{m.group(3)}", text)


def user_facing_error(exc: Exception) -> str:
    if isinstance(exc, (ProcessingError, BudgetExceededError, ConfigurationError, AIResponseError, AudioError)):
        return str(exc)
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(status, int):
        return f"Внешний сервис ИИ вернул ошибку {status}. Повторите попытку позже."
    return "Внутренняя ошибка обработки. Повторите попытку или обратитесь к администратору."


class ConsultationService:
    """Оркестратор: аудио -> текст -> роли -> черновик заключения и памятки.

    Тяжёлые сервисы (Gemini, STT, pyannote) создаются лениво, поэтому текстовый режим
    работает без torch и без ключей распознавания речи.
    """

    def __init__(self, db: Session, *, ai_service=None, stt_service=None, diarization_service=None,
                 diarization_resolved: bool = False):
        self.db = db
        self.consultation_repository = ConsultationRepository(db)
        self.document_repository = MedicalDocumentRepository(db)
        self.memo_repository = PatientMemoRepository(db)
        self.audio_file_repository = AudioFileRepository(db)
        self.transcript_repository = TranscriptRepository(db)
        self.usage = UsageService(db)
        self.transcript_alignment_service = TranscriptAlignmentService()
        self._ai = ai_service
        self._stt = stt_service
        self._diar = diarization_service
        self._diar_resolved = diarization_resolved or diarization_service is not None

    # ---------- ленивые зависимости ----------
    @property
    def ai_service(self):
        if self._ai is None:
            from app.services.factory import get_ai_service
            self._ai = get_ai_service()
        return self._ai

    @property
    def audio_transcription_service(self):
        if self._stt is None:
            from app.services.factory import get_stt_service
            self._stt = get_stt_service()
        return self._stt

    @property
    def audio_diarization_service(self):
        if not self._diar_resolved:
            from app.services.factory import get_diarization_service
            self._diar = get_diarization_service()
            self._diar_resolved = True
        return self._diar

    # ---------- создание записей ----------
    def create_text_consultation(
        self, *, patient_name: str, doctor_name: str, consultation_date: str,
        dialogue_text: str, doctor_id: int | None = None,
    ) -> Consultation:
        return self.consultation_repository.create(
            patient_name=patient_name, doctor_name=doctor_name, consultation_date=consultation_date,
            raw_dialogue_text=dialogue_text, source=ConsultationSource.TEXT, doctor_id=doctor_id,
        )

    def create_audio_consultation(
        self, *, patient_name: str, doctor_name: str, consultation_date: str,
        audio_path: str, duration_seconds: float | None, doctor_id: int | None = None,
    ) -> Consultation:
        consultation = self.consultation_repository.create(
            patient_name=patient_name, doctor_name=doctor_name, consultation_date=consultation_date,
            raw_dialogue_text="", source=ConsultationSource.AUDIO, doctor_id=doctor_id,
        )
        self.audio_file_repository.create(
            consultation_id=consultation.id, file_path=audio_path,
            duration_seconds=int(duration_seconds) if duration_seconds else None,
        )
        return consultation

    # ---------- синхронные сценарии (CLI) ----------
    def process_text_consultation(self, patient_name, doctor_name, consultation_date, dialogue_text):
        consultation = self.create_text_consultation(
            patient_name=patient_name, doctor_name=doctor_name,
            consultation_date=consultation_date, dialogue_text=dialogue_text,
        )
        self.run_text_processing(consultation.id, raise_errors=True)
        return self._result_tuple(consultation.id, with_audio=False)

    def process_audio_consultation(self, patient_name, doctor_name, consultation_date, audio_path):
        consultation = self.create_audio_consultation(
            patient_name=patient_name, doctor_name=doctor_name, consultation_date=consultation_date,
            audio_path=audio_path, duration_seconds=None,
        )
        self.run_audio_processing(consultation.id, raise_errors=True)
        return self._result_tuple(consultation.id, with_audio=True)

    def _result_tuple(self, consultation_id: int, with_audio: bool):
        self.db.expire_all()
        c = self.consultation_repository.get_by_id(consultation_id)
        if with_audio:
            return c, c.audio_file, c.transcript, c.medical_document, c.patient_memo
        return c, c.medical_document, c.patient_memo

    # ---------- фоновые сценарии (API) ----------
    def run_text_processing(self, consultation_id: int, raise_errors: bool = False) -> None:
        consultation = self.consultation_repository.get_by_id(consultation_id)
        if consultation is None:
            return
        try:
            self._generate_document(consultation)
            self._finish(consultation)
        except Exception as exc:
            self._fail(consultation_id, exc)
            if raise_errors:
                raise

    def run_audio_processing(self, consultation_id: int, raise_errors: bool = False) -> None:
        consultation = self.consultation_repository.get_by_id(consultation_id)
        if consultation is None:
            return
        try:
            self._process_audio(consultation)
            self._generate_document(consultation)
            self._finish(consultation)
        except Exception as exc:
            self._fail(consultation_id, exc)
            if raise_errors:
                raise

    def regenerate(self, consultation_id: int) -> None:
        """Повторная генерация: из текущего текста диалога; для аудио без расшифровки — весь конвейер."""
        consultation = self.consultation_repository.get_by_id(consultation_id)
        if consultation is None:
            return
        needs_audio = (
            consultation.source == ConsultationSource.AUDIO and not (consultation.dialogue_text or "").strip()
        )
        if needs_audio:
            self.run_audio_processing(consultation_id)
        else:
            self.run_text_processing(consultation_id)

    # ---------- внутренние шаги ----------
    def _stage(self, consultation: Consultation, stage: str) -> None:
        self.consultation_repository.set_progress(
            consultation, status=ConsultationStatus.PROCESSING, stage=stage
        )

    def _process_audio(self, consultation: Consultation) -> None:
        audio = consultation.audio_file
        if audio is None or audio.is_deleted or not Path(audio.file_path).exists():
            raise ProcessingError("Аудиофайл недоступен (удалён или не найден).")
        path = str(audio.file_path)

        # Диаризация идёт первой: она локальная и бесплатная — если сломается, мы не потратим деньги на STT.
        turns = []
        diarizer = self.audio_diarization_service
        if diarizer is not None:
            self._stage(consultation, "diarizing")
            turns = diarizer.diarize(path)

        self._stage(consultation, "transcribing")
        stt = self.audio_transcription_service

        if stt.supports_segments:
            result = stt.transcribe_audio(path)
            self.usage.record_stt(consultation.id, result.provider, result.model, result.duration_seconds)
            if turns:
                speaker_segments = self.transcript_alignment_service.align(result.segments, turns)
            else:
                speaker_segments = [
                    SpeakerTranscriptSegment(start=s.start, end=s.end, speaker=UNKNOWN_SPEAKER, text=s.text)
                    for s in result.segments if s.text.strip()
                ]
            full_text, raw_json, seconds = result.text, result.raw_json, result.duration_seconds
        elif turns:
            per_turn = stt.transcribe_turns(path, turns)
            self.usage.record_stt(consultation.id, per_turn.provider, per_turn.model, per_turn.billed_seconds)
            speaker_segments, full_text, raw_json = per_turn.segments, per_turn.text, per_turn.raw_json
            seconds = per_turn.billed_seconds
        else:
            result = stt.transcribe_audio(path)
            self.usage.record_stt(consultation.id, result.provider, result.model, result.duration_seconds)
            speaker_segments = (
                [SpeakerTranscriptSegment(start=0.0, end=result.duration_seconds, speaker=UNKNOWN_SPEAKER,
                                          text=result.text.strip())]
                if result.text.strip() else []
            )
            full_text, raw_json, seconds = result.text, result.raw_json, result.duration_seconds

        if not full_text.strip() or not speaker_segments:
            raise ProcessingError("В записи не удалось распознать речь. Проверьте качество аудио.")

        if seconds and not audio.duration_seconds:
            self.audio_file_repository.set_duration(audio, int(seconds))

        speaker_transcript = build_speaker_transcript(speaker_segments)

        self._stage(consultation, "structuring")
        dialogue_result, usage = self.ai_service.process_dialogue(speaker_transcript)
        self.usage.record_llm(consultation.id, self.ai_service.provider_name, usage)

        notes: list[str] = []
        if dialogue_result.processing_notes:
            notes.append("Заметки обработки:")
            notes.extend(dialogue_result.processing_notes)
        if dialogue_result.uncertain_segments:
            notes.append("Неуверенные фрагменты:")
            notes.extend(dialogue_result.uncertain_segments)

        self.transcript_repository.create(
            consultation_id=consultation.id,
            full_text=full_text,
            raw_response_json=raw_json,
            cleaned_text=dialogue_result.cleaned_text,
            role_separated_text=dialogue_result.role_separated_text,
            cleanup_notes="\n".join(notes),
        )
        consultation.raw_dialogue_text = dialogue_result.role_separated_text
        consultation.dialogue_text = dialogue_result.role_separated_text
        self.db.commit()

    def _generate_document(self, consultation: Consultation) -> None:
        dialogue = (consultation.dialogue_text or consultation.raw_dialogue_text or "").strip()
        if not dialogue:
            raise ProcessingError("Текст диалога пуст.")

        self._stage(consultation, "generating")
        output, usage = self.ai_service.generate_consultation_output(dialogue)
        self.usage.record_llm(consultation.id, self.ai_service.provider_name, usage)

        warnings = validate_generated_output(dialogue, output)
        self.document_repository.create(consultation.id, output.medical_document, warnings)
        self.memo_repository.create(consultation.id, output.patient_memo)

    def _finish(self, consultation: Consultation) -> None:
        consultation.confirmed_at = None
        consultation.confirmed_by_id = None
        self.consultation_repository.set_progress(
            consultation, status=ConsultationStatus.DRAFT_CREATED, stage=None, error=None
        )
        if settings.delete_audio_after_processing and consultation.audio_file \
                and not consultation.audio_file.is_deleted:
            AudioRetentionService(self.db).delete_audio(consultation.audio_file)

    def _fail(self, consultation_id: int, exc: Exception) -> None:
        logger.exception("Обработка консультации %s не удалась", consultation_id)
        self.db.rollback()
        consultation = self.consultation_repository.get_by_id(consultation_id)
        if consultation is not None:
            self.consultation_repository.set_progress(
                consultation, status=ConsultationStatus.FAILED, stage=None, error=user_facing_error(exc)
            )
