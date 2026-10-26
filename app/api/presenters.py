import json

from app.models.consultation import Consultation, ConsultationStatus
from app.schemas.api import (
    AudioInfo, ConsultationDetail, ConsultationSummary, MedicalDocumentOut, PatientMemoOut,
)


def summary(c: Consultation) -> ConsultationSummary:
    return ConsultationSummary(
        id=c.id, patient_name=c.patient_name, doctor_name=c.doctor_name,
        consultation_date=c.consultation_date, status=c.status, source=c.source,
        progress_stage=c.progress_stage, created_at=c.created_at, confirmed_at=c.confirmed_at,
    )


def _loads_list(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw) if raw else []
    except ValueError:
        return []
    return [str(v) for v in value] if isinstance(value, list) else []


def detail(c: Consultation) -> ConsultationDetail:
    doc, memo, audio, transcript = c.medical_document, c.patient_memo, c.audio_file, c.transcript
    return ConsultationDetail(
        **summary(c).model_dump(),
        error_message=c.error_message,
        output_locale=c.output_locale,
        document_type=c.document_type,
        template_fields=json.loads(c.template_fields_json or "{}"),
        dialogue_text=c.dialogue_text,
        transcript_notes=transcript.cleanup_notes if transcript else None,
        document=MedicalDocumentOut(
            complaints=doc.complaints or "", anamnesis=doc.anamnesis or "",
            symptoms_duration=doc.symptoms_duration or "", examination=doc.examination or "",
            diagnosis=doc.diagnosis or "", treatment_plan=doc.treatment_plan or "",
            diagnosis_code=doc.diagnosis_code,
            recommendations=doc.recommendations or "",
            missing_information=[m for m in (doc.missing_information or "").splitlines() if m.strip()],
            validation_warnings=_loads_list(doc.validation_warnings),
            edited_at=doc.edited_at,
        ) if doc else None,
        memo=PatientMemoOut(memo_text=memo.memo_text, edited_at=memo.edited_at) if memo else None,
        audio=AudioInfo(
            available=bool(audio and not audio.is_deleted), format=audio.file_format if audio else None,
            duration_seconds=audio.duration_seconds if audio else None,
            deleted_at=audio.deleted_at if audio else None,
        ),
        confirmed_by=c.confirmed_by.full_name if c.confirmed_by else None,
        can_edit=c.status == ConsultationStatus.DRAFT_CREATED,
    )
