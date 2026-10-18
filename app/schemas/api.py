"""Схемы HTTP API (вход/выход). Схемы вывода ИИ лежат в соседних файлах."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- Пользователи и вход ----------
class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=2, max_length=255)
    password: str
    role: str = "doctor"


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None  # сброс пароля администратором


# ---------- Консультации ----------
class TextConsultationCreate(BaseModel):
    patient_name: str = Field(min_length=1, max_length=255)
    consultation_date: str = Field(min_length=1, max_length=50)
    dialogue_text: str = Field(min_length=10)
    doctor_name: str | None = Field(default=None, max_length=255)


class MedicalDocumentOut(BaseModel):
    complaints: str = ""
    anamnesis: str = ""
    symptoms_duration: str = ""
    examination: str = ""
    diagnosis: str = ""
    treatment_plan: str = ""
    recommendations: str = ""
    missing_information: list[str] = []
    validation_warnings: list[str] = []
    edited_at: datetime | None = None


class MedicalDocumentUpdate(BaseModel):
    complaints: str | None = None
    anamnesis: str | None = None
    symptoms_duration: str | None = None
    examination: str | None = None
    diagnosis: str | None = None
    treatment_plan: str | None = None
    recommendations: str | None = None
    missing_information: list[str] | None = None


class PatientMemoOut(BaseModel):
    memo_text: str = ""
    edited_at: datetime | None = None


class PatientMemoUpdate(BaseModel):
    memo_text: str


class DialogueUpdate(BaseModel):
    dialogue_text: str = Field(min_length=1)


class RegenerateRequest(BaseModel):
    # Без подтверждения нельзя затереть ручные правки врача.
    confirm_overwrite: bool = False


class AudioInfo(BaseModel):
    available: bool
    format: str | None = None
    duration_seconds: int | None = None
    deleted_at: datetime | None = None


class ConsultationSummary(BaseModel):
    id: int
    patient_name: str
    doctor_name: str
    consultation_date: str
    status: str
    source: str
    progress_stage: str | None = None
    created_at: datetime
    confirmed_at: datetime | None = None


class ConsultationDetail(ConsultationSummary):
    error_message: str | None = None
    dialogue_text: str | None = None
    transcript_notes: str | None = None
    document: MedicalDocumentOut | None = None
    memo: PatientMemoOut | None = None
    audio: AudioInfo = AudioInfo(available=False)
    confirmed_by: str | None = None
    can_edit: bool = False


class ConsultationStatusOut(BaseModel):
    id: int
    status: str
    progress_stage: str | None = None
    error_message: str | None = None


class ConsultationList(BaseModel):
    items: list[ConsultationSummary]
    total: int


# ---------- Администрирование ----------
class UsageByModel(BaseModel):
    kind: str
    provider: str
    model: str
    cost_usd: float
    audio_minutes: float
    input_tokens: int
    output_tokens: int


class UsageByDay(BaseModel):
    day: str
    cost_usd: float


class UsageSummary(BaseModel):
    month: str
    total_cost_usd: float
    budget_usd: float
    budget_used_percent: float | None
    consultations_processed: int
    avg_cost_per_consultation_usd: float | None
    by_model: list[UsageByModel]
    by_day: list[UsageByDay]


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    user_email: str | None
    action: str
    entity_type: str | None
    entity_id: int | None
    details: str | None
    ip_address: str | None
    created_at: datetime


class AuditLogList(BaseModel):
    items: list[AuditLogOut]
    total: int


class PurgeResult(BaseModel):
    deleted_files: int
