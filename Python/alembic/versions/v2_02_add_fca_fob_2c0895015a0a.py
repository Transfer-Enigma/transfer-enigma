"""v2.2-add-fca-fob

Revision ID: 2c0895015a0a
Revises: c572f6e1d3d9
Create Date: 2026-04-23 13:36:39.895495

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '2c0895015a0a'
down_revision: Union[str, Sequence[str], None] = 'c572f6e1d3d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # I DON'T KNOW WHY PARAMETERS 'existing_type' and 'type' ARE INVERTED!!!
    op.alter_column('routes', 'container_shipment_terms',
                    existing_type=mysql.ENUM('FOR', 'FOB', 'FCA'),
                    type=mysql.ENUM('FOR'),
                    nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # I DON'T KNOW WHY PARAMETERS 'existing_type' and 'type' ARE INVERTED!!!
    op.alter_column('routes', 'container_shipment_terms',
                    existing_type=mysql.ENUM('FOR'),
                    type=mysql.ENUM('FOR', 'FOB', 'FCA'),
                    nullable=False)
