"""v2.7-routes-timetable

Revision ID: 2b4c35a59f44
Revises: 814b3b174c24
Create Date: 2026-05-14 02:55:49.905016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2b4c35a59f44'
down_revision: Union[str, Sequence[str], None] = '814b3b174c24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('routes', sa.Column('timetable', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('routes', 'timetable')
