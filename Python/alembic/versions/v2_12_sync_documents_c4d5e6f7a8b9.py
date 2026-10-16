"""v2.12-sync-documents

Revision ID: c4d5e6f7a8b9
Revises: 2f8718f90318
Create Date: 2026-10-01 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = '2f8718f90318'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'sync_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False, server_default='gsheets'),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('sea_ws', sa.String(length=200), nullable=True),
        sa.Column('rail_ws', sa.String(length=200), nullable=True),
        sa.Column('truck_ws', sa.String(length=200), nullable=True),
        sa.Column('dropp_ws', sa.String(length=200), nullable=True),
        sa.Column('points_ws', sa.String(length=200), nullable=True),
        sa.Column('services_ws', sa.String(length=200), nullable=True),
        sa.Column('uid_column', sa.String(length=100), nullable=False, server_default='__uid'),
        sa.Column('last_status', sa.String(length=50), nullable=True),
        sa.Column('last_errors_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('loaded_at', sa.DateTime(timezone=False), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('sync_documents')
