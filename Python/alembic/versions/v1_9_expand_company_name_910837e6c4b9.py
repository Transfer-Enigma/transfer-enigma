"""v1.9-extend-company-name

Revision ID: 910837e6c4b9
Revises: cb29d1f22aab
Create Date: 2026-04-10 20:28:31.470227

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '910837e6c4b9'
down_revision: Union[str, Sequence[str], None] = 'cb29d1f22aab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('companies', 'name',
               existing_type=mysql.VARCHAR(length=30),
               type_=sa.String(length=150),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # CAN NOT DELETE COMPANIES WITH A LONG NAME
    op.alter_column('companies', 'name',
               existing_type=sa.String(length=150),
               type_=mysql.VARCHAR(length=30),
               existing_nullable=False)
