"""v2.0-add-services

Revision ID: 0327cc7e8404
Revises: 910837e6c4b9
Create Date: 2026-04-16 19:48:15.079246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0327cc7e8404'
down_revision: Union[str, Sequence[str], None] = '910837e6c4b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'services',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('hint', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'service_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('route_id', sa.Integer(), nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['route_id'], ['routes.id'], name='fk__service_prices_route'),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], name='fk__service_prices_service'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('route_id', 'service_id', name='uk__fingerprint')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('service_prices')
    op.drop_table('services')
