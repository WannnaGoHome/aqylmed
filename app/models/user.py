from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.timeutils import utcnow


class UserRole:
    DOCTOR = "doctor"
    ADMIN = "admin"
    ALL = (DOCTOR, ADMIN)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=UserRole.DOCTOR)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    specialty_id: Mapped[int | None] = mapped_column(
        ForeignKey("medical_specialties.id", ondelete="SET NULL"), nullable=True, index=True
    )
    locale: Mapped[str] = mapped_column(String(5), default="ru")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verification_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email_verification_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    two_factor_challenge_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    two_factor_code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    two_factor_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    two_factor_attempts: Mapped[int] = mapped_column(Integer, default=0)
    password_reset_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    specialty = relationship("MedicalSpecialty")
