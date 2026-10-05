"""v2.12-route-collections

Revision ID: c7d2e4a9b1f3
Revises: 2f8718f90318
Create Date: 2026-10-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7d2e4a9b1f3"
down_revision: Union[str, Sequence[str], None] = "2f8718f90318"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "route_collections",
        sa.Column("uid", sa.String(length=32), nullable=False),
        sa.Column("demo_uid", sa.String(length=64), nullable=True),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("uid"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_route_collections_demo_uid", "route_collections", ["demo_uid"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_route_collections_demo_uid", table_name="route_collections")
    op.drop_table("route_collections")
