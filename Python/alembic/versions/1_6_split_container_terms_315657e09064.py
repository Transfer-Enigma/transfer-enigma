"""1.6-split-container-terms

Revision ID: 315657e09064
Revises: ab161f8f7484
Create Date: 2026-04-02 16:14:35.882649

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '315657e09064'
down_revision: Union[str, Sequence[str], None] = 'ab161f8f7484'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('prices', sa.Column('container_shipment_terms', sa.Enum('FOR', name='containershipmentterms', create_constraint=True), nullable=False, default='FOR'))
    op.execute('UPDATE prices SET container_transfer_terms="FILO" WHERE container_transfer_terms="FOBFOR"')

    op.alter_column('prices', 'container_transfer_terms',
                    existing_type=mysql.ENUM('FIFO', 'FIFOR', 'FILO'),
                    nullable=False)
    op.execute('UPDATE prices SET container_transfer_terms="FIFO" WHERE container_transfer_terms="FIFOR"')

    op.alter_column('prices', 'container_transfer_terms',
               existing_type=mysql.ENUM('FIFO', 'FILO'),
               nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('prices', 'container_transfer_terms',
                    existing_type=mysql.ENUM('FIFO', 'FIFOR', 'FILO'),
                    nullable=False)
    op.execute('UPDATE prices SET container_transfer_terms="FIFOR" WHERE container_transfer_terms="FIFO"')

    op.alter_column('prices', 'container_transfer_terms',
               existing_type=mysql.ENUM('FIFOR', 'FILO', 'FOBFOR'),
               nullable=True)
    op.execute('UPDATE prices SET container_transfer_terms="FOBFOR" WHERE id IN (SELECT p.id FROM routes r JOIN prices p ON r.id=p.route_id WHERE r.type="rail")')

    op.drop_column('prices', 'container_shipment_terms')
