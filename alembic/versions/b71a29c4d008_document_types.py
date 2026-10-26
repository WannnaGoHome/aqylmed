"""Document types and stable template snapshots.

Revision ID: b71a29c4d008
Revises: 4f8a3d2c91be
"""
from alembic import op
import sqlalchemy as sa

revision = 'b71a29c4d008'
down_revision = '4f8a3d2c91be'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('consultations', sa.Column('document_type', sa.String(30), nullable=False, server_default='initial'))
    op.add_column('consultations', sa.Column('template_fields_json', sa.Text(), nullable=True))
    with op.batch_alter_table('medical_document_templates') as batch:
        batch.add_column(sa.Column('document_type', sa.String(30), nullable=False, server_default='initial'))
        batch.drop_constraint('uq_template_specialty_locale', type_='unique')
        batch.create_unique_constraint('uq_template_specialty_locale', ['specialty_id', 'locale', 'document_type'])
    op.execute(sa.text("""
        UPDATE consultations SET template_fields_json = COALESCE((
            SELECT t.fields_json FROM medical_document_templates t
            JOIN users u ON u.specialty_id = t.specialty_id
            WHERE u.id = consultations.doctor_id
              AND t.locale = COALESCE(consultations.output_locale, u.locale, 'ru')
              AND t.document_type = 'initial'
        ), '{}')
    """))


def downgrade():
    # Do not silently discard examination/discharge templates.
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT count(*) FROM medical_document_templates WHERE document_type <> 'initial'")).scalar():
        raise RuntimeError('Export and remove examination/discharge templates before downgrade')
    with op.batch_alter_table('medical_document_templates') as batch:
        batch.drop_constraint('uq_template_specialty_locale', type_='unique')
        batch.drop_column('document_type')
        batch.create_unique_constraint('uq_template_specialty_locale', ['specialty_id', 'locale'])
    op.drop_column('consultations', 'template_fields_json')
    op.drop_column('consultations', 'document_type')
