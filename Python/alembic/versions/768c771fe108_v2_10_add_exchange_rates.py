"""v2_10_add_exchange_rates

Revision ID: 768c771fe108
Revises: 763e59003748
Create Date: 2026-06-18 10:34:15.795539

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "768c771fe108"
down_revision: Union[str, Sequence[str], None] = "763e59003748"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "date", name="uq_exchange_rates_code_date")
    )
    op.create_index(op.f("ix_exchange_rates_code"), "exchange_rates", ["code"], unique=False)
    op.create_index(op.f("ix_exchange_rates_date"), "exchange_rates", ["date"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_exchange_rates_date"), table_name="exchange_rates")
    op.drop_index(op.f("ix_exchange_rates_code"), table_name="exchange_rates")
    op.drop_table("exchange_rates")
