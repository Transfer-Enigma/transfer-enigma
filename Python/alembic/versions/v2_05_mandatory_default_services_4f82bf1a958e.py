"""v2.5-mandatory-default-services

Revision ID: 4f82bf1a958e
Revises: a93d697f85b1
Create Date: 2026-04-27 18:30:03.919422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4f82bf1a958e'
down_revision: Union[str, Sequence[str], None] = 'a93d697f85b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('services', sa.Column('mandatory', sa.Boolean(), nullable=False))
    op.add_column('services', sa.Column('default', sa.Boolean(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('services', 'default')
    op.drop_column('services', 'mandatory')
