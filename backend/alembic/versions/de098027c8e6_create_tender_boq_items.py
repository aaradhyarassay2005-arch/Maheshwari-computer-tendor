"""create tender_boq_items

Revision ID: de098027c8e6
Revises: 80036bf9eae5
Create Date: 2026-06-06 15:06:24.636332

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de098027c8e6'
down_revision: Union[str, None] = '80036bf9eae5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('tender_boq_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tender_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=True),
        sa.Column('item_code', sa.String(length=50), nullable=True),
        sa.Column('item_name', sa.String(), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('unit_rate', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('amount', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('schedule_name', sa.String(length=255), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['tender_documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tender_boq_items_tender_id', 'tender_boq_items', ['tender_id'], unique=False)
    op.create_index('ix_tender_boq_items_document_id', 'tender_boq_items', ['document_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_tender_boq_items_document_id', table_name='tender_boq_items')
    op.drop_index('ix_tender_boq_items_tender_id', table_name='tender_boq_items')
    op.drop_table('tender_boq_items')

