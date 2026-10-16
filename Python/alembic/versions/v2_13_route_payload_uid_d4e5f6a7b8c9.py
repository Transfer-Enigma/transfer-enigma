"""v2.13-route-payload-uid

Revision ID: d4e5f6a7b8c9
Revises: c4d5e6f7a8b9
Create Date: 2026-10-01 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('routes', sa.Column('payload_hash', sa.String(length=64), nullable=True))
    op.create_unique_constraint('uq__routes_payload_hash', 'routes', ['payload_hash'])
    op.add_column('routes', sa.Column('sync_document_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk__route_sync_document', 'routes', 'sync_documents',
        ['sync_document_id'], ['id'], ondelete='SET NULL',
    )
    op.drop_constraint('uk__fingerprint', 'routes', type_='unique')
    op.create_unique_constraint(
        'uk__fingerprint', 'routes',
        ['type', 'company_id', 'start_point_id', 'end_point_id', 'dropp_off_point_id',
         'effective_from', 'effective_to', 'container_shipment_terms', 'container_transfer_terms',
         'container_owner', 'is_through'],
    )

    op.add_column('drop', sa.Column('payload_hash', sa.String(length=64), nullable=True))
    op.create_unique_constraint('uq__drop_payload_hash', 'drop', ['payload_hash'])
    op.add_column('drop', sa.Column('sync_document_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk__drop_sync_document', 'drop', 'sync_documents',
        ['sync_document_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk__drop_sync_document', 'drop', type_='foreignkey')
    op.drop_column('drop', 'sync_document_id')
    op.drop_constraint('uq__drop_payload_hash', 'drop', type_='unique')
    op.drop_column('drop', 'payload_hash')

    op.drop_constraint('uk__fingerprint', 'routes', type_='unique')
    op.create_unique_constraint(
        'uk__fingerprint', 'routes',
        ['company_id', 'start_point_id', 'end_point_id', 'dropp_off_point_id',
         'effective_from', 'effective_to', 'container_shipment_terms', 'container_transfer_terms',
         'container_owner', 'is_through'],
    )
    op.drop_constraint('fk__route_sync_document', 'routes', type_='foreignkey')
    op.drop_column('routes', 'sync_document_id')
    op.drop_constraint('uq__routes_payload_hash', 'routes', type_='unique')
    op.drop_column('routes', 'payload_hash')
