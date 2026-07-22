"""v2_10_add_setting_locked

Revision ID: 63b7b144c602
Revises: 9721e23b56a3
Create Date: 2026-06-25 17:23:16.279102

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '63b7b144c602'
down_revision: Union[str, Sequence[str], None] = '9721e23b56a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add locked column to settings table."""
    op.add_column('settings', sa.Column('locked', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Remove locked column from settings table."""
    op.drop_column('settings', 'locked')
