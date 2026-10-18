from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.timeutils import utcnow


class MedicalDocument(Base):
    __tablename__ = "medical_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    consultation_id: Mapped[int] = mapped_column(
        ForeignKey("consultations.id", ondelete="CASCADE"), unique=True, index=True
    )

    complaints: Mapped[str | None] = mapped_column(Text, nullable=True)
    anamnesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    symptoms_duration: Mapped[str | None] = mapped_column(Text, nullable=True)
    examination: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    treatment_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Список, склеенный через "\n" (формат сохранён из этапа 1).
    missing_information: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON-снимок того, что сгенерировал ИИ, — нужен для оценки точности на пилоте
    # (сравнение черновика ИИ с тем, что подтвердил врач).
    ai_original_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON-список предупреждений автоматической проверки (числа/дозировки без опоры в диалоге).
    validation_warnings: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    consultation = relationship(
        "Consultation",
        back_populates="medical_document",
    )
