"""create_past_projects_table

Revision ID: cefd2672cb2e
Revises: de098027c8e6
Create Date: 2026-06-06 15:20:32.068878

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cefd2672cb2e'
down_revision: Union[str, None] = 'de098027c8e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('past_projects',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_name', sa.String(length=255), nullable=False),
        sa.Column('client', sa.String(length=255), nullable=False),
        sa.Column('project_value', sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column('completion_date', sa.Date(), nullable=True),
        sa.Column('domain', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('document_path', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_past_projects_domain', 'past_projects', ['domain'], unique=False)
    op.create_index('ix_past_projects_location', 'past_projects', ['location'], unique=False)
    op.create_index('ix_past_projects_project_value', 'past_projects', ['project_value'], unique=False)
    op.create_index('ix_past_projects_created_at', 'past_projects', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_past_projects_created_at', table_name='past_projects')
    op.drop_index('ix_past_projects_project_value', table_name='past_projects')
    op.drop_index('ix_past_projects_location', table_name='past_projects')
    op.drop_index('ix_past_projects_domain', table_name='past_projects')
    op.drop_table('past_projects')

