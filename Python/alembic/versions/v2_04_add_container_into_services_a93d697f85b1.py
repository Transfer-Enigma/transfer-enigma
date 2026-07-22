"""v2.4-add-container-into-services

Revision ID: a93d697f85b1
Revises: c2a5990862b7
Create Date: 2026-04-25 01:20:27.137338

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a93d697f85b1'
down_revision: Union[str, Sequence[str], None] = 'c2a5990862b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('service_prices', sa.Column('container_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk__service_prices_container', 'service_prices', 'containers', ['container_id'], ['id'])

    # Add 'container_id' into UID
    op.create_unique_constraint(op.f('uk__fingerprint_old'), 'service_prices', ['route_id', 'service_id', 'container_id'])
    op.drop_constraint('uk__fingerprint', 'service_prices', type_='unique')
    op.create_unique_constraint(op.f('uk__fingerprint'), 'service_prices', ['route_id', 'service_id', 'container_id'])
    op.drop_constraint('uk__fingerprint_old', 'service_prices', type_='unique')


def downgrade() -> None:
    """Downgrade schema."""
    # Remove new-format data
    op.execute("DELETE FROM `service_prices` WHERE `container_id` IS NOT NULL")

    # Remove 'container_id' from UID
    op.create_unique_constraint(op.f('uk__fingerprint_old'), 'service_prices', ['route_id', 'service_id'])
    op.drop_constraint('uk__fingerprint', 'service_prices', type_='unique')
    op.create_unique_constraint(op.f('uk__fingerprint'), 'service_prices', ['route_id', 'service_id'])
    op.drop_constraint('uk__fingerprint_old', 'service_prices', type_='unique')

    op.drop_constraint('fk__service_prices_container', 'service_prices', type_='foreignkey')
    op.drop_column('service_prices', 'container_id')
