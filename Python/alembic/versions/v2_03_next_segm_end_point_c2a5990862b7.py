"""v2.3-next-segm-end-point

Revision ID: c2a5990862b7
Revises: 2c0895015a0a
Create Date: 2026-04-24 00:41:41.547020

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c2a5990862b7'
down_revision: Union[str, Sequence[str], None] = '2c0895015a0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('routes', sa.Column('dropp_off_point_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk__route_point__dropp_off', 'routes', 'points', ['dropp_off_point_id'], ['id'])

    # Swap routes constraint
    op.create_unique_constraint('uk__fingerprint_1', 'routes', ['company_id', 'start_point_id', 'end_point_id', 'dropp_off_point_id', 'effective_from', 'effective_to', 'container_shipment_terms', 'container_transfer_terms', 'container_owner', 'is_through'])
    op.drop_constraint('uk__fingerprint', 'routes', type_='unique')
    op.create_unique_constraint('uk__fingerprint', 'routes', ['company_id', 'start_point_id', 'end_point_id', 'dropp_off_point_id', 'effective_from', 'effective_to', 'container_shipment_terms', 'container_transfer_terms', 'container_owner', 'is_through'])
    op.drop_constraint('uk__fingerprint_1', 'routes', type_='unique')



def downgrade() -> None:
    """Downgrade schema."""
    # Remove all routes with new column
    op.execute("DELETE FROM `routes` WHERE `dropp_off_point_id` IS NOT NULL")

    # Swap routes constraint
    op.create_unique_constraint('uk__fingerprint_1', 'routes', ['company_id', 'start_point_id', 'end_point_id', 'effective_from', 'effective_to', 'container_shipment_terms', 'container_transfer_terms', 'container_owner', 'is_through'])
    op.drop_constraint('uk__fingerprint', 'routes', type_='unique')
    op.create_unique_constraint('uk__fingerprint', 'routes', ['company_id', 'start_point_id', 'end_point_id', 'effective_from', 'effective_to', 'container_shipment_terms', 'container_transfer_terms', 'container_owner', 'is_through'])
    op.drop_constraint('uk__fingerprint_1', 'routes', type_='unique')

    op.drop_constraint('fk__route_point__dropp_off', 'routes', type_='foreignkey')
    op.drop_column('routes', 'dropp_off_point_id')
