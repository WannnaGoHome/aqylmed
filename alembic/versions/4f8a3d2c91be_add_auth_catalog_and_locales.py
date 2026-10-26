"""Add auth, specialty and medical-code catalog fields.

Revision ID: 4f8a3d2c91be
Revises: fd4f3fbfb451
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "4f8a3d2c91be"
down_revision: Union[str, Sequence[str], None] = "fd4f3fbfb451"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("consultations", sa.Column("output_locale", sa.String(5), nullable=True))
    op.create_table(
        "medical_specialties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name_ru", sa.String(255), nullable=False),
        sa.Column("name_kk", sa.String(255), nullable=False, server_default=""),
        sa.Column("name_en", sa.String(255), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "medical_document_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("specialty_id", sa.Integer(), sa.ForeignKey("medical_specialties.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("fields_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("specialty_id", "locale", name="uq_template_specialty_locale"),
    )
    op.create_index("ix_medical_document_templates_specialty_id", "medical_document_templates", ["specialty_id"])
    op.create_table(
        "icd10_codes",
        sa.Column("code", sa.String(10), primary_key=True),
        sa.Column("name_ru", sa.String(500), nullable=False),
        sa.Column("name_kk", sa.String(500), nullable=False, server_default=""),
        sa.Column("name_en", sa.String(500), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.add_column("users", sa.Column("specialty_id", sa.Integer(), nullable=True))
    op.create_index("ix_users_specialty_id", "users", ["specialty_id"])
    op.create_foreign_key("users_specialty_id_fkey", "users", "medical_specialties",
                          ["specialty_id"], ["id"], ondelete="SET NULL")
    op.add_column("users", sa.Column("locale", sa.String(5), nullable=False, server_default="ru"))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("email_verification_hash", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("email_verification_expires_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("two_factor_challenge_hash", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("two_factor_code_hash", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("two_factor_expires_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("two_factor_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("password_reset_hash", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("password_reset_expires_at", sa.DateTime(), nullable=True))
    op.add_column("medical_documents", sa.Column("diagnosis_code", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("consultations", "output_locale")
    op.drop_column("medical_documents", "diagnosis_code")
    op.drop_column("users", "password_reset_expires_at")
    op.drop_column("users", "password_reset_hash")
    op.drop_column("users", "two_factor_attempts")
    op.drop_column("users", "two_factor_expires_at")
    op.drop_column("users", "two_factor_code_hash")
    op.drop_column("users", "two_factor_challenge_hash")
    op.drop_column("users", "locale")
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_hash")
    op.drop_column("users", "email_verified")
    op.drop_constraint("users_specialty_id_fkey", "users", type_="foreignkey")
    op.drop_index("ix_users_specialty_id", "users")
    op.drop_column("users", "specialty_id")
    op.drop_table("icd10_codes")
    op.drop_index("ix_medical_document_templates_specialty_id", "medical_document_templates")
    op.drop_table("medical_document_templates")
    op.drop_table("medical_specialties")
