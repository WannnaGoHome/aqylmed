from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MedicalSpecialty(Base):
    __tablename__ = "medical_specialties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_ru: Mapped[str] = mapped_column(String(255))
    name_kk: Mapped[str] = mapped_column(String(255), default="")
    name_en: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    templates = relationship("MedicalDocumentTemplate", back_populates="specialty")


class MedicalDocumentTemplate(Base):
    __tablename__ = "medical_document_templates"
    __table_args__ = (UniqueConstraint("specialty_id", "locale", "document_type", name="uq_template_specialty_locale"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    specialty_id: Mapped[int] = mapped_column(ForeignKey("medical_specialties.id", ondelete="CASCADE"), index=True)
    locale: Mapped[str] = mapped_column(String(5))
    document_type: Mapped[str] = mapped_column(String(30), default="initial")
    fields_json: Mapped[str] = mapped_column(Text)

    specialty = relationship("MedicalSpecialty", back_populates="templates")


class Icd10Code(Base):
    __tablename__ = "icd10_codes"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name_ru: Mapped[str] = mapped_column(String(500))
    name_kk: Mapped[str] = mapped_column(String(500), default="")
    name_en: Mapped[str] = mapped_column(String(500), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
