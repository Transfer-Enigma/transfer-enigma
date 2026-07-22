"""v2.6-add-LIFO-LILO

Revision ID: 814b3b174c24
Revises: 4f82bf1a958e
Create Date: 2026-05-09 00:29:20.735069

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '814b3b174c24'
down_revision: Union[str, Sequence[str], None] = '4f82bf1a958e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # I DON'T KNOW WHY PARAMETERS 'existing_type' and 'type' ARE INVERTED!!!
    op.alter_column('routes', 'container_transfer_terms',
                    existing_type=mysql.ENUM('FIFO', 'FILO', 'LIFO', 'LILO'),
                    type=mysql.ENUM('FIFO', 'FILO'),
                    nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # I DON'T KNOW WHY PARAMETERS 'existing_type' and 'type' ARE INVERTED!!!
    op.alter_column('routes', 'container_transfer_terms',
                    existing_type=mysql.ENUM('FIFO', 'FILO'),
                    type=mysql.ENUM('FIFO', 'FILO', 'LIFO', 'LILO'),
                    nullable=False)
