"""update_documents_and_add_metadata

Revision ID: 80036bf9eae5
Revises: 624387f57cfa
Create Date: 2026-06-06 14:56:25.594824

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80036bf9eae5'
down_revision: Union[str, None] = '624387f57cfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop download_history table
    op.drop_index('ix_download_history_tender_id', table_name='download_history')
    op.drop_table('download_history')

    # 2. Modify tender_documents table
    # Drop index on old column name
    op.drop_index('ix_tender_documents_sha256_hash', table_name='tender_documents')

    # Rename sha256_hash to sha256
    op.execute('ALTER TABLE tender_documents RENAME COLUMN sha256_hash TO sha256')
    
    # Create index on new column name
    op.create_index('ix_tender_documents_sha256', 'tender_documents', ['sha256'], unique=True)

    # Alter nullable constraints for download lifecycle fields
    op.alter_column('tender_documents', 'file_path', existing_type=sa.String(length=1000), nullable=True)
    op.alter_column('tender_documents', 'file_size', existing_type=sa.Integer(), server_default='0', nullable=False)
    op.alter_column('tender_documents', 'mime_type', existing_type=sa.String(length=100), nullable=True)
    op.alter_column('tender_documents', 'sha256', existing_type=sa.String(length=64), nullable=True)

    # Add new columns
    op.add_column('tender_documents', sa.Column('file_name', sa.String(length=255), nullable=True))
    op.add_column('tender_documents', sa.Column('downloaded_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tender_documents', sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False))
    op.add_column('tender_documents', sa.Column('attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('tender_documents', sa.Column('error_message', sa.String(length=1000), nullable=True))

    op.create_index('ix_tender_documents_status', 'tender_documents', ['status'], unique=False)

    # 3. Create tender_metadata table
    op.create_table('tender_metadata',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tender_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=True),
        sa.Column('tender_number', sa.String(length=255), nullable=True),
        sa.Column('tender_number_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('department_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('tender_value', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('tender_value_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('emd', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('emd_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('closing_date', sa.Date(), nullable=True),
        sa.Column('closing_date_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('completion_period', sa.String(length=255), nullable=True),
        sa.Column('completion_period_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('tender_type', sa.String(length=100), nullable=True),
        sa.Column('tender_type_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('zone', sa.String(length=100), nullable=True),
        sa.Column('zone_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('bid_system', sa.String(length=100), nullable=True),
        sa.Column('bid_system_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('contract_type', sa.String(length=100), nullable=True),
        sa.Column('contract_type_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['tender_documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tender_metadata_document_id'), 'tender_metadata', ['document_id'], unique=True)
    op.create_index(op.f('ix_tender_metadata_tender_id'), 'tender_metadata', ['tender_id'], unique=True)


def downgrade() -> None:
    # 1. Drop tender_metadata table
    op.drop_index(op.f('ix_tender_metadata_tender_id'), table_name='tender_metadata')
    op.drop_index(op.f('ix_tender_metadata_document_id'), table_name='tender_metadata')
    op.drop_table('tender_metadata')

    # 2. Modify tender_documents table
    op.drop_index('ix_tender_documents_status', table_name='tender_documents')
    op.drop_column('tender_documents', 'error_message')
    op.drop_column('tender_documents', 'attempts')
    op.drop_column('tender_documents', 'status')
    op.drop_column('tender_documents', 'downloaded_at')
    op.drop_column('tender_documents', 'file_name')

    op.alter_column('tender_documents', 'sha256', existing_type=sa.String(length=64), nullable=False)
    op.alter_column('tender_documents', 'mime_type', existing_type=sa.String(length=100), nullable=False)
    op.alter_column('tender_documents', 'file_size', existing_type=sa.Integer(), server_default=None, nullable=False)
    op.alter_column('tender_documents', 'file_path', existing_type=sa.String(length=1000), nullable=False)

    op.drop_index('ix_tender_documents_sha256', table_name='tender_documents')
    op.execute('ALTER TABLE tender_documents RENAME COLUMN sha256 TO sha256_hash')
    op.create_index('ix_tender_documents_sha256_hash', 'tender_documents', ['sha256_hash'], unique=True)

    # 3. Recreate download_history table
    op.create_table('download_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tender_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_download_history_tender_id', 'download_history', ['tender_id'], unique=False)

