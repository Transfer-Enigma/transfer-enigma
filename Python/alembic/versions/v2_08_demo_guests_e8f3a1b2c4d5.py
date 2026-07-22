"""v2.8-demo-guests

Revision ID: e8f3a1b2c4d5
Revises: 2b4c35a59f44
Create Date: 2026-05-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e8f3a1b2c4d5"
down_revision: Union[str, Sequence[str], None] = "2b4c35a59f44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "demo_guests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uid", sa.String(length=64), nullable=False),
        sa.Column("sea_profit", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("sea_profit_currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("rail_profit", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("rail_profit_currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uid"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_demo_guests_uid", "demo_guests", ["uid"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_demo_guests_uid", table_name="demo_guests")
    op.drop_table("demo_guests")
