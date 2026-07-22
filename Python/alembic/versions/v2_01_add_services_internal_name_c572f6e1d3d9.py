"""v2.1-add-services-internal-name

Revision ID: c572f6e1d3d9
Revises: 0327cc7e8404
Create Date: 2026-04-18 01:38:05.025593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c572f6e1d3d9'
down_revision: Union[str, Sequence[str], None] = '0327cc7e8404'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('services', sa.Column('internal_name', sa.String(length=100), nullable=False))

    conn = op.get_bind()
    Services = sa.Table('services', sa.MetaData(), autoload_with=conn)
    for i, row in enumerate(conn.execute(Services.select())):
        conn.execute(Services.update().where(Services.c.id == row.id).values(internal_name=i))

    op.create_unique_constraint(None, 'services', ['internal_name'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('internal_name', 'services', type_='unique')
    op.drop_column('services', 'internal_name')
