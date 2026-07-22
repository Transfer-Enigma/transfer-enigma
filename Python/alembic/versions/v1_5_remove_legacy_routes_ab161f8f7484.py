"""v1.5-remove-legacy-routes

Revision ID: ab161f8f7484
Revises: 638ad167c6bd
Create Date: 2026-04-01 23:12:15.551996

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'ab161f8f7484'
down_revision: Union[str, Sequence[str], None] = '638ad167c6bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Delete old unsupported data
    op.execute('DELETE FROM `routes` WHERE type="SEA_RAIL"')
    op.execute('DELETE FROM `prices` WHERE type="MIXED"')

    op.add_column('prices', sa.Column('container_transfer_terms', sa.Enum('FIFOR', 'FILO', 'FOBFOR', name='containertransferterms', create_constraint=True), nullable=False))
    op.execute('UPDATE `prices` SET `container_transfer_terms`=`type`')

    op.execute('ALTER TABLE `routes` MODIFY COLUMN `type` ENUM("SEA", "RAIL")')

    op.create_unique_constraint('uk__fingerprint_new', 'prices', ['route_id', 'container_id', 'container_transfer_terms', 'container_owner'])
    op.drop_index(op.f('uk__fingerprint'), 'prices')
    op.create_unique_constraint('uk__fingerprint', 'prices', ['route_id', 'container_id', 'container_transfer_terms', 'container_owner'])
    op.drop_index(op.f('uk__fingerprint_new'), 'prices')

    op.drop_column('prices', 'type')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('prices', sa.Column('type', mysql.ENUM('FIFOR', 'FILO', 'FOBFOR', 'MIXED'), nullable=False))
    op.execute('UPDATE `prices` SET `type`=`container_transfer_terms`')

    op.execute('ALTER TABLE `routes` MODIFY COLUMN `type` ENUM("SEA", "RAIL", "SEA_RAIL")')

    op.create_unique_constraint(op.f('uk__fingerprint_old'), 'prices', ['route_id', 'container_id', 'type', 'container_owner'])
    op.drop_constraint('uk__fingerprint', 'prices', type_='unique')
    op.create_unique_constraint(op.f('uk__fingerprint'), 'prices', ['route_id', 'container_id', 'type', 'container_owner'])
    op.drop_constraint('uk__fingerprint_old', 'prices', type_='unique')

    op.drop_column('prices', 'container_transfer_terms')
