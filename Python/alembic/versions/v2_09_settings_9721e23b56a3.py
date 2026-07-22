"""v2_9_settings

Revision ID: 9721e23b56a3
Revises: e8f3a1b2c4d5
Create Date: 2026-06-23 22:07:33.673929

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9721e23b56a3'
down_revision: Union[str, Sequence[str], None] = 'e8f3a1b2c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('value_type',
                  sa.Enum('BOOL', 'INT', 'FLOAT', 'STRING', 'JSON', name='settingtype', create_constraint=True),
                  nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group', 'name', name='uk__setting_group_name')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('settings')
