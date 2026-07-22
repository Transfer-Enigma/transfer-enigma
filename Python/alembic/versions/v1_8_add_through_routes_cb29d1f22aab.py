"""v1.8-is-through-route

Revision ID: cb29d1f22aab
Revises: f1014438b53f
Create Date: 2026-04-09 20:56:38.149090

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'cb29d1f22aab'
down_revision: Union[str, Sequence[str], None] = 'f1014438b53f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('routes', sa.Column('is_through', sa.Boolean(create_constraint=True), nullable=False, server_default='1'))

    op.create_unique_constraint('uk__fingerprint_1', 'routes', ['company_id', 'start_point_id', 'end_point_id', 'effective_from', 'effective_to', 'container_shipment_terms', 'container_transfer_terms', 'container_owner', 'is_through'])
    op.drop_constraint(op.f('uk__fingerprint'), 'routes', type_='unique')
    op.create_unique_constraint('uk__fingerprint', 'routes', ['company_id', 'start_point_id', 'end_point_id', 'effective_from', 'effective_to', 'container_shipment_terms', 'container_transfer_terms', 'container_owner', 'is_through'])
    op.drop_constraint(op.f('uk__fingerprint_1'), 'routes', type_='unique')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_unique_constraint(op.f('uk__fingerprint_1'), 'routes', ['company_id', 'start_point_id', 'end_point_id', 'effective_from', 'effective_to', 'container_shipment_terms', 'container_transfer_terms', 'container_owner'])
    op.drop_constraint('uk__fingerprint', 'routes', type_='unique')

    op.drop_column('routes', 'is_through')

    op.create_unique_constraint(op.f('uk__fingerprint'), 'routes', ['company_id', 'start_point_id', 'end_point_id', 'effective_from', 'effective_to', 'container_shipment_terms', 'container_transfer_terms', 'container_owner'])
    op.drop_constraint('uk__fingerprint_1', 'routes', type_='unique')
