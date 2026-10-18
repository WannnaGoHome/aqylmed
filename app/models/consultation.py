from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.timeutils import utcnow


class ConsultationStatus:
    PROCESSING = "processing"        # идёт распознавание / генерация
    DRAFT_CREATED = "draft_created"  # черновик готов, ждёт врача
    CONFIRMED = "confirmed"          # врач подтвердил
    FAILED = "failed"                # обработка завершилась ошибкой


class ConsultationSource:
    TEXT = "text"
    AUDIO = "audio"


class Consultation(Base):
    __tablename__ = "consultations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_name: Mapped[str] = mapped_column(String(255))
    doctor_name: Mapped[str] = mapped_column(String(255))
    consultation_date: Mapped[str] = mapped_column(String(50))

    # Исходный текст диалога, как он пришёл на вход (для аудио — диалог с ролями после обработки).
    raw_dialogue_text: Mapped[str] = mapped_column(Text, default="")
    # Рабочая версия диалога: её врач может править, из неё генерируется заключение.
    dialogue_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(50), default=ConsultationStatus.PROCESSING)
    source: Mapped[str] = mapped_column(String(20), default=ConsultationSource.TEXT)
    progress_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    doctor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    confirmed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    medical_document = relationship(
        "MedicalDocument",
        back_populates="consultation",
        uselist=False,
        cascade="all, delete-orphan",
    )

    patient_memo = relationship(
        "PatientMemo",
        back_populates="consultation",
        uselist=False,
        cascade="all, delete-orphan",
    )

    audio_file = relationship(
        "AudioFile",
        back_populates="consultation",
        uselist=False,
        cascade="all, delete-orphan",
    )

    transcript = relationship(
        "Transcript",
        back_populates="consultation",
        uselist=False,
        cascade="all, delete-orphan",
    )

    doctor = relationship("User", foreign_keys=[doctor_id])
    confirmed_by = relationship("User", foreign_keys=[confirmed_by_id])
