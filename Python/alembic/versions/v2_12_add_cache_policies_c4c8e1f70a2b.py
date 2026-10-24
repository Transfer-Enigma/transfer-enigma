"""v2_12_add_cache_policies

Revision ID: c4c8e1f70a2b
Revises: 2f8718f90318
Create Date: 2026-10-22 02:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c4c8e1f70a2b'
down_revision: Union[str, Sequence[str], None] = '2f8718f90318'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the cache_policies table."""
    op.create_table(
        'cache_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('entity', sa.String(length=50), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('ttl', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source', 'entity', name='uk__cache_policy_source_entity')
    )


def downgrade() -> None:
    """Drop the cache_policies table."""
    op.drop_table('cache_policies')
