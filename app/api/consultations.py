import logging
import json
import uuid
from pathlib import Path

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, Response,
    UploadFile, status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api import presenters
from app.api.deps import get_consultation_or_404, get_current_user, get_runner, require_admin
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import BudgetExceededError
from app.core.timeutils import utcnow
from app.models.consultation import ConsultationStatus
from app.models.medical_catalog import Icd10Code
from app.models.medical_catalog import MedicalDocumentTemplate
from app.models.user import User
from app.repositories.consultation_repository import ConsultationRepository
from app.repositories.medical_document_repository import MedicalDocumentRepository
from app.repositories.patient_memo_repository import PatientMemoRepository
from app.schemas.api import (
    DocumentType, ConsultationDetail, ConsultationList, ConsultationStatusOut, DialogueUpdate,
    MedicalDocumentUpdate, PatientMemoUpdate, RegenerateRequest, TextConsultationCreate,
)
from app.services import export_service
from app.services.audio_utils import ALLOWED_EXTENSIONS, AudioError, normalize_audio, probe_duration
from app.services.audit_service import AuditService
from app.services.consultation_service import ConsultationService, swap_roles
from app.services.retention_service import AudioRetentionService
from app.services.runner import ProcessingRunner
from app.services.usage_service import UsageService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/consultations", tags=["consultations"])

_AUDIO_MEDIA_TYPES = {
    "flac": "audio/flac", "wav": "audio/wav", "ogg": "audio/ogg", "mp3": "audio/mpeg",
}


def _check_budget(db: Session) -> None:
    try:
        UsageService(db).check_budget()
    except BudgetExceededError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))


def _conflict(message: str, code: str | None = None):
    return HTTPException(status.HTTP_409_CONFLICT, {"message": message, "code": code})


# ---------- список и создание ----------
@router.get("", response_model=ConsultationList)
def list_consultations(
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    items, total = ConsultationRepository(db).list(
        doctor_id=None if user.role == "admin" else user.id,
        status=status_filter, query=q, limit=limit, offset=offset,
    )
    return ConsultationList(items=[presenters.summary(c) for c in items], total=total)


@router.post("/text", response_model=ConsultationStatusOut, status_code=202)
def create_text_consultation(
    payload: TextConsultationCreate, request: Request, background: BackgroundTasks,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
    runner: ProcessingRunner = Depends(get_runner),
):
    _check_budget(db)
    consultation = ConsultationService(db).create_text_consultation(
        patient_name=payload.patient_name.strip(),
        doctor_name=(payload.doctor_name or user.full_name).strip(),
        consultation_date=payload.consultation_date.strip(),
        dialogue_text=payload.dialogue_text, doctor_id=user.id,
    )
    consultation.document_type = payload.document_type
    db.commit()
    AuditService(db).log("consultation.create", user=user, entity_type="consultation",
                         entity_id=consultation.id, details={"source": "text"}, request=request)
    background.add_task(runner.run, consultation.id, "text")
    return ConsultationStatusOut(id=consultation.id, status=consultation.status,
                                 progress_stage=consultation.progress_stage)


@router.post("/audio", response_model=ConsultationStatusOut, status_code=202)
async def create_audio_consultation(
    request: Request, background: BackgroundTasks,
    patient_name: str = Form(..., min_length=1, max_length=255),
    consultation_date: str = Form(..., min_length=1, max_length=50),
    consent_confirmed: bool = Form(...),
    document_type: DocumentType = Form("initial"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
    runner: ProcessingRunner = Depends(get_runner),
):
    if not consent_confirmed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Подтвердите, что пациент дал согласие на запись и обработку разговора"
        )
    _check_budget(db)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Формат {suffix or 'файла'} не поддерживается. Допустимо: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    upload_dir = Path(settings.upload_dir)
    tmp_dir = upload_dir / "_incoming"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    stem = uuid.uuid4().hex  # имя файла не зависит от пользовательского ввода
    tmp_path = tmp_dir / f"{stem}{suffix}"

    max_bytes = settings.max_upload_mb * 1024 * 1024
    written = 0
    try:
        with tmp_path.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        413,
                        f"Файл больше {settings.max_upload_mb} МБ",
                    )
                out.write(chunk)
        if written == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Файл пустой")
        try:
            final_path = normalize_audio(tmp_path, upload_dir, stem)
        except AudioError as exc:
            raise HTTPException(422, str(exc))
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    duration = probe_duration(final_path)
    consultation = ConsultationService(db).create_audio_consultation(
        patient_name=patient_name.strip(), doctor_name=user.full_name,
        consultation_date=consultation_date.strip(), audio_path=str(final_path),
        duration_seconds=duration, doctor_id=user.id,
    )
    consultation.document_type = document_type
    db.commit()
    AuditService(db).log("consultation.create", user=user, entity_type="consultation",
                         entity_id=consultation.id, details={"source": "audio", "patient_consent_confirmed": True},
                         request=request)
    background.add_task(runner.run, consultation.id, "audio")
    return ConsultationStatusOut(id=consultation.id, status=consultation.status,
                                 progress_stage=consultation.progress_stage)


# ---------- просмотр ----------
@router.get("/{consultation_id}/status", response_model=ConsultationStatusOut)
def get_status(consultation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = get_consultation_or_404(db, consultation_id, user)
    return ConsultationStatusOut(id=c.id, status=c.status, progress_stage=c.progress_stage,
                                 error_message=c.error_message)


@router.get("/{consultation_id}", response_model=ConsultationDetail)
def get_consultation(
    consultation_id: int, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    c = get_consultation_or_404(db, consultation_id, user)
    AuditService(db).log("consultation.view", user=user, entity_type="consultation",
                         entity_id=c.id, request=request)
    return presenters.detail(c)


# ---------- редактирование ----------
@router.put("/{consultation_id}/document", response_model=ConsultationDetail)
def update_document(
    consultation_id: int, payload: MedicalDocumentUpdate, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    c = get_consultation_or_404(db, consultation_id, user)
    if c.status != ConsultationStatus.DRAFT_CREATED or c.medical_document is None:
        raise _conflict("Заключение можно редактировать только в статусе «Черновик»")
    changes = payload.model_dump(exclude_unset=True)
    code = changes.get("diagnosis_code", c.medical_document.diagnosis_code)
    diagnosis = changes.get("diagnosis", c.medical_document.diagnosis)
    code_entry = db.get(Icd10Code, code.upper()) if code else None
    if code and (code_entry is None or not code_entry.is_active):
        raise HTTPException(422, "Выберите действующий код МКБ-10 из справочника")
    if (
        (diagnosis or "").strip()
        and db.query(Icd10Code).filter(Icd10Code.is_active.is_(True)).count()
        and not code
    ):
        raise HTTPException(422, "Для диагноза обязательно укажите код МКБ-10")
    MedicalDocumentRepository(db).update_fields(c.medical_document, changes)
    AuditService(db).log("document.edit", user=user, entity_type="consultation", entity_id=c.id,
                         details={"fields": sorted(changes)}, request=request)
    return presenters.detail(c)


@router.put("/{consultation_id}/memo", response_model=ConsultationDetail)
def update_memo(
    consultation_id: int, payload: PatientMemoUpdate, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    c = get_consultation_or_404(db, consultation_id, user)
    if c.status != ConsultationStatus.DRAFT_CREATED or c.patient_memo is None:
        raise _conflict("Памятку можно редактировать только в статусе «Черновик»")
    PatientMemoRepository(db).update_text(c.patient_memo, payload.memo_text)
    AuditService(db).log("memo.edit", user=user, entity_type="consultation", entity_id=c.id, request=request)
    return presenters.detail(c)


@router.put("/{consultation_id}/dialogue", response_model=ConsultationDetail)
def update_dialogue(
    consultation_id: int, payload: DialogueUpdate, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    c = get_consultation_or_404(db, consultation_id, user)
    if c.status not in (ConsultationStatus.DRAFT_CREATED, ConsultationStatus.FAILED):
        raise _conflict("Диалог нельзя менять во время обработки или после подтверждения")
    c.dialogue_text = payload.dialogue_text
    db.commit()
    AuditService(db).log("dialogue.edit", user=user, entity_type="consultation", entity_id=c.id, request=request)
    return presenters.detail(c)


@router.post("/{consultation_id}/swap-roles", response_model=ConsultationDetail)
def swap_dialogue_roles(
    consultation_id: int, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    c = get_consultation_or_404(db, consultation_id, user)
    if c.status not in (ConsultationStatus.DRAFT_CREATED, ConsultationStatus.FAILED) or not c.dialogue_text:
        raise _conflict("Роли можно поменять только в готовом диалоге до подтверждения")
    c.dialogue_text = swap_roles(c.dialogue_text)
    db.commit()
    AuditService(db).log("dialogue.swap_roles", user=user, entity_type="consultation",
                         entity_id=c.id, request=request)
    return presenters.detail(c)


@router.post("/{consultation_id}/regenerate", response_model=ConsultationStatusOut, status_code=202)
def regenerate(
    consultation_id: int, payload: RegenerateRequest, request: Request, background: BackgroundTasks,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
    runner: ProcessingRunner = Depends(get_runner),
):
    c = get_consultation_or_404(db, consultation_id, user)
    if c.status not in (ConsultationStatus.DRAFT_CREATED, ConsultationStatus.FAILED):
        raise _conflict("Перегенерация доступна для черновика или после ошибки")
    edited = bool(
        (c.medical_document and c.medical_document.edited_at) or (c.patient_memo and c.patient_memo.edited_at)
    )
    if edited and not payload.confirm_overwrite:
        raise _conflict("Ваши правки в заключении будут потеряны", "edits_would_be_lost")
    _check_budget(db)
    ConsultationRepository(db).set_progress(c, status=ConsultationStatus.PROCESSING, stage="queued")
    AuditService(db).log("consultation.regenerate", user=user, entity_type="consultation",
                         entity_id=c.id, request=request)
    background.add_task(runner.run, c.id, "regenerate")
    return ConsultationStatusOut(id=c.id, status=c.status, progress_stage=c.progress_stage)


# ---------- подтверждение ----------
@router.post("/{consultation_id}/confirm", response_model=ConsultationDetail)
def confirm(
    consultation_id: int, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    c = get_consultation_or_404(db, consultation_id, user)
    if c.status != ConsultationStatus.DRAFT_CREATED or c.medical_document is None:
        raise _conflict("Подтвердить можно только готовый черновик")
    if not (c.medical_document.diagnosis_code or "").strip():
        raise HTTPException(422, "Для подтверждения обязательно выберите код МКБ-10 из справочника")
    entry = db.get(Icd10Code, c.medical_document.diagnosis_code.upper()) if c.medical_document.diagnosis_code else None
    if c.medical_document.diagnosis_code and (entry is None or not entry.is_active):
        raise HTTPException(422, "Код МКБ-10 не найден в справочнике")
    c.status = ConsultationStatus.CONFIRMED
    c.confirmed_at = utcnow()
    c.confirmed_by_id = user.id
    db.commit()
    db.refresh(c)
    AuditService(db).log("consultation.confirm", user=user, entity_type="consultation",
                         entity_id=c.id, request=request)
    return presenters.detail(c)


@router.post("/{consultation_id}/reopen", response_model=ConsultationDetail)
def reopen(
    consultation_id: int, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    c = get_consultation_or_404(db, consultation_id, user)
    if c.status != ConsultationStatus.CONFIRMED:
        raise _conflict("Вернуть к редактированию можно только подтверждённое заключение")
    c.status = ConsultationStatus.DRAFT_CREATED
    c.confirmed_at = None
    c.confirmed_by_id = None
    db.commit()
    db.refresh(c)
    AuditService(db).log("consultation.reopen", user=user, entity_type="consultation",
                         entity_id=c.id, request=request)
    return presenters.detail(c)


# ---------- аудио ----------
@router.get("/{consultation_id}/audio")
def get_audio(
    consultation_id: int, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    c = get_consultation_or_404(db, consultation_id, user)
    audio = c.audio_file
    if audio is None or audio.is_deleted or not Path(audio.file_path).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Аудиозапись недоступна или удалена")
    AuditService(db).log("audio.access", user=user, entity_type="consultation",
                         entity_id=c.id, request=request)
    return FileResponse(audio.file_path, media_type=_AUDIO_MEDIA_TYPES.get(audio.file_format, "application/octet-stream"))


@router.delete("/{consultation_id}/audio", status_code=204)
def delete_audio(
    consultation_id: int, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    c = get_consultation_or_404(db, consultation_id, user)
    if c.status == ConsultationStatus.PROCESSING:
        raise _conflict("Нельзя удалить запись во время обработки")
    if c.audio_file is None or c.audio_file.is_deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Аудиозапись уже удалена")
    AudioRetentionService(db).delete_audio(c.audio_file)
    AuditService(db).log("audio.delete", user=user, entity_type="consultation", entity_id=c.id, request=request)


# ---------- экспорт ----------
@router.get("/{consultation_id}/export")
def export(
    consultation_id: int, request: Request,
    format: str = Query(default="docx", pattern="^(docx|txt)$"),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    c = get_consultation_or_404(db, consultation_id, user)
    if c.medical_document is None:
        raise _conflict("Заключение ещё не готово")
    AuditService(db).log("consultation.export", user=user, entity_type="consultation",
                         entity_id=c.id, details={"format": format}, request=request)
    locale = c.output_locale or user.locale
    field_labels = json.loads(c.template_fields_json or "{}")
    if format == "docx":
        body = export_service.export_docx(c, locale, field_labels)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        body = export_service.export_txt(c, locale, field_labels).encode("utf-8")
        media = "text/plain; charset=utf-8"
    return Response(body, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="consultation_{c.id}.{format}"'})


# ---------- удаление (администратор) ----------
@router.delete("/{consultation_id}", status_code=204)
def delete_consultation(
    consultation_id: int, request: Request,
    user: User = Depends(require_admin), db: Session = Depends(get_db),
):
    c = get_consultation_or_404(db, consultation_id, user)
    if c.status == ConsultationStatus.PROCESSING:
        raise _conflict("Нельзя удалить приём во время обработки")
    if c.audio_file and not c.audio_file.is_deleted:
        AudioRetentionService(db).delete_audio(c.audio_file)
    ConsultationRepository(db).delete(c)
    AuditService(db).log("consultation.delete", user=user, entity_type="consultation",
                         entity_id=consultation_id, request=request)
