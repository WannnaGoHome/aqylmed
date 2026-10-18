from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, validate_password_strength
from app.models.user import User, UserRole
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.schemas.api import (
    AuditLogList, AuditLogOut, PurgeResult, UsageSummary, UserCreate, UserOut, UserUpdate,
)
from app.services.audio_utils import ffmpeg_available
from app.services.audit_service import AuditService
from app.services.retention_service import AudioRetentionService
from app.services.usage_service import UsageService

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return UserRepository(db).list()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate, request: Request,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    if payload.role not in UserRole.ALL:
        raise HTTPException(422, "Недопустимая роль")
    if "@" not in payload.email:
        raise HTTPException(422, "Укажите корректный email")
    problem = validate_password_strength(payload.password)
    if problem:
        raise HTTPException(422, problem)
    if repo.get_by_email(payload.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким email уже есть")
    user = repo.create(
        email=payload.email, full_name=payload.full_name,
        hashed_password=hash_password(payload.password), role=payload.role,
    )
    AuditService(db).log("user.create", user=admin, entity_type="user", entity_id=user.id,
                         details={"role": user.role}, request=request)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, payload: UserUpdate, request: Request,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    changes = payload.model_dump(exclude_unset=True)

    if "role" in changes and changes["role"] not in UserRole.ALL:
        raise HTTPException(422, "Недопустимая роль")
    loses_admin = user.role == UserRole.ADMIN and user.is_active and (
        changes.get("is_active") is False or changes.get("role", UserRole.ADMIN) != UserRole.ADMIN
    )
    if loses_admin and repo.count_active_admins() <= 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя отключить или понизить последнего администратора")

    if changes.get("password"):
        problem = validate_password_strength(changes["password"])
        if problem:
            raise HTTPException(422, problem)
        user.hashed_password = hash_password(changes["password"])
    for field in ("full_name", "role", "is_active"):
        if field in changes and changes[field] is not None:
            setattr(user, field, changes[field])
    repo.save(user)
    AuditService(db).log(
        "user.update", user=admin, entity_type="user", entity_id=user.id,
        details={"fields": sorted(k for k in changes if k != "password") + (["password"] if "password" in changes else [])},
        request=request,
    )
    return user


@router.get("/usage", response_model=UsageSummary)
def usage(month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), db: Session = Depends(get_db)):
    return UsageService(db).summary(month)


@router.get("/audit", response_model=AuditLogList)
def audit(
    action: str | None = None, user_id: int | None = None, entity_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = AuditRepository(db).list(
        action=action, user_id=user_id, entity_id=entity_id, limit=limit, offset=offset
    )
    return AuditLogList(items=[AuditLogOut.model_validate(i) for i in items], total=total)


@router.post("/retention/purge", response_model=PurgeResult)
def purge_audio(request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    deleted = AudioRetentionService(db).purge_expired()
    AuditService(db).log("retention.purge", user=admin, details={"deleted_files": deleted}, request=request)
    return PurgeResult(deleted_files=deleted)


@router.get("/system")
def system_info():
    """Состояние конфигурации без секретов — чтобы администратор видел, что подключено."""
    return {
        "environment": settings.environment,
        "stt_provider": settings.stt_provider,
        "stt_model": settings.groq_stt_model if settings.stt_provider == "groq" else settings.openai_stt_model,
        "stt_key_configured": bool(settings.groq_api_key if settings.stt_provider == "groq" else settings.openai_api_key),
        "llm_model": settings.gemini_model,
        "llm_key_configured": bool(settings.gemini_api_key),
        "diarization_enabled": settings.diarization_enabled,
        "hf_token_configured": bool(settings.hf_token),
        "ffmpeg_available": ffmpeg_available(),
        "audio_retention_days": settings.audio_retention_days,
        "delete_audio_after_processing": settings.delete_audio_after_processing,
        "monthly_budget_usd": settings.monthly_api_budget_usd,
    }
