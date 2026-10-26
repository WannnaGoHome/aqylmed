# Импорт всех моделей нужен, чтобы Base.metadata знал о каждой таблице (Alembic, create_all).
from app.models.audio_file import AudioFile
from app.models.audit_log import AuditLog
from app.models.consultation import Consultation, ConsultationSource, ConsultationStatus
from app.models.medical_document import MedicalDocument
from app.models.medical_catalog import Icd10Code, MedicalDocumentTemplate, MedicalSpecialty
from app.models.patient_memo import PatientMemo
from app.models.transcript import Transcript
from app.models.usage_record import UsageKind, UsageRecord
from app.models.user import User, UserRole

__all__ = [
    "AudioFile",
    "AuditLog",
    "Consultation",
    "ConsultationSource",
    "ConsultationStatus",
    "MedicalDocument",
    "Icd10Code",
    "MedicalDocumentTemplate",
    "MedicalSpecialty",
    "PatientMemo",
    "Transcript",
    "UsageKind",
    "UsageRecord",
    "User",
    "UserRole",
]
