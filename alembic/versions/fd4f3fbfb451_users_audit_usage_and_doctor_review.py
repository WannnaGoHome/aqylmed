"""users, audit log, usage records and doctor review workflow

Revision ID: fd4f3fbfb451
Revises: cb162674da0a
Create Date: 2026-10-18 12:32:54

Что делает миграция:
  * добавляет таблицы users, audit_logs, usage_records;
  * расширяет consultations / medical_documents / patient_memos для проверки врачом;
  * делает связь «консультация -> заключение/памятка/аудио/расшифровка» строго 1:1
    и включает каскадное удаление;
  * переносит уже существующие записи: dialogue_text = raw_dialogue_text,
    source = 'audio' для консультаций с аудио, updated_at = created_at.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'fd4f3fbfb451'
down_revision: Union[str, Sequence[str], None] = 'cb162674da0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHILD_TABLES = ("audio_files", "medical_documents", "patient_memos", "transcripts")


def upgrade() -> None:
    # --- новые таблицы -----------------------------------------------------
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=80), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='audit_logs_user_id_fkey', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)

    op.create_table(
        'usage_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('consultation_id', sa.Integer(), nullable=True),
        sa.Column('kind', sa.String(length=10), nullable=False),
        sa.Column('provider', sa.String(length=40), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('audio_seconds', sa.Float(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['consultation_id'], ['consultations.id'],
            name='usage_records_consultation_id_fkey', ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_usage_records_consultation_id'), 'usage_records', ['consultation_id'], unique=False)
    op.create_index(op.f('ix_usage_records_created_at'), 'usage_records', ['created_at'], unique=False)
    op.create_index(op.f('ix_usage_records_id'), 'usage_records', ['id'], unique=False)

    # --- consultations: новые колонки с переносом старых данных -------------
    op.add_column('consultations', sa.Column('dialogue_text', sa.Text(), nullable=True))
    op.execute("UPDATE consultations SET dialogue_text = raw_dialogue_text")

    op.add_column('consultations', sa.Column('source', sa.String(length=20), nullable=False, server_default='text'))
    op.execute("UPDATE consultations SET source = 'audio' WHERE id IN (SELECT consultation_id FROM audio_files)")
    op.alter_column('consultations', 'source', server_default=None)

    op.add_column('consultations', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.execute("UPDATE consultations SET updated_at = created_at")
    op.alter_column('consultations', 'updated_at', nullable=False)

    op.add_column('consultations', sa.Column('progress_stage', sa.String(length=50), nullable=True))
    op.add_column('consultations', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('consultations', sa.Column('doctor_id', sa.Integer(), nullable=True))
    op.add_column('consultations', sa.Column('confirmed_by_id', sa.Integer(), nullable=True))
    op.add_column('consultations', sa.Column('confirmed_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_consultations_doctor_id'), 'consultations', ['doctor_id'], unique=False)
    op.create_foreign_key(
        'consultations_doctor_id_fkey', 'consultations', 'users', ['doctor_id'], ['id'], ondelete='SET NULL'
    )
    op.create_foreign_key(
        'consultations_confirmed_by_id_fkey', 'consultations', 'users', ['confirmed_by_id'], ['id'],
        ondelete='SET NULL',
    )

    # --- medical_documents / patient_memos ----------------------------------
    op.add_column('medical_documents', sa.Column('symptoms_duration', sa.Text(), nullable=True))
    op.add_column('medical_documents', sa.Column('ai_original_json', sa.Text(), nullable=True))
    op.add_column('medical_documents', sa.Column('validation_warnings', sa.Text(), nullable=True))
    op.add_column('medical_documents', sa.Column('edited_at', sa.DateTime(), nullable=True))
    op.add_column('patient_memos', sa.Column('ai_original_text', sa.Text(), nullable=True))
    op.add_column('patient_memos', sa.Column('edited_at', sa.DateTime(), nullable=True))

    # --- связь 1:1 + каскадное удаление -------------------------------------
    for table in _CHILD_TABLES:
        op.drop_constraint(f'{table}_consultation_id_fkey', table, type_='foreignkey')
        op.create_foreign_key(
            f'{table}_consultation_id_fkey', table, 'consultations', ['consultation_id'], ['id'],
            ondelete='CASCADE',
        )
        op.create_index(f'ix_{table}_consultation_id', table, ['consultation_id'], unique=True)


def downgrade() -> None:
    for table in reversed(_CHILD_TABLES):
        op.drop_index(f'ix_{table}_consultation_id', table_name=table)
        op.drop_constraint(f'{table}_consultation_id_fkey', table, type_='foreignkey')
        op.create_foreign_key(
            f'{table}_consultation_id_fkey', table, 'consultations', ['consultation_id'], ['id']
        )

    op.drop_column('patient_memos', 'edited_at')
    op.drop_column('patient_memos', 'ai_original_text')
    op.drop_column('medical_documents', 'edited_at')
    op.drop_column('medical_documents', 'validation_warnings')
    op.drop_column('medical_documents', 'ai_original_json')
    op.drop_column('medical_documents', 'symptoms_duration')

    op.drop_constraint('consultations_confirmed_by_id_fkey', 'consultations', type_='foreignkey')
    op.drop_constraint('consultations_doctor_id_fkey', 'consultations', type_='foreignkey')
    op.drop_index(op.f('ix_consultations_doctor_id'), table_name='consultations')
    for column in (
        'confirmed_at', 'confirmed_by_id', 'doctor_id', 'error_message',
        'progress_stage', 'updated_at', 'source', 'dialogue_text',
    ):
        op.drop_column('consultations', column)

    op.drop_index(op.f('ix_usage_records_id'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_created_at'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_consultation_id'), table_name='usage_records')
    op.drop_table('usage_records')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
