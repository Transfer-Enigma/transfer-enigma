"""v2.11-add-truck-route-type

Revision ID: 2f8718f90318
Revises: 63b7b144c602
Create Date: 2026-07-10 20:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '2f8718f90318'
down_revision: Union[str, Sequence[str], None] = '63b7b144c602'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # I DON'T KNOW WHY PARAMETERS 'existing_type' and 'type' ARE INVERTED!!!
    op.alter_column('routes', 'type',
                    existing_type=mysql.ENUM('SEA', 'RAIL', 'TRUCK'),
                    type=mysql.ENUM('SEA', 'RAIL'),
                    nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # I DON'T KNOW WHY PARAMETERS 'existing_type' and 'type' ARE INVERTED!!!
    op.execute("DELETE FROM `routes` WHERE `type`='TRUCK'")
    op.alter_column('routes', 'type',
                    existing_type=mysql.ENUM('SEA', 'RAIL'),
                    type=mysql.ENUM('SEA', 'RAIL', 'TRUCK'),
                    nullable=False)
