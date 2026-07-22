"""v1.3-normalize-drop

Revision ID: 569fbebd37d5
Revises: 2cfce045e792
Create Date: 2026-04-01 22:40:13.842688

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '569fbebd37d5'
down_revision: Union[str, Sequence[str], None] = '2cfce045e792'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Delete old unsupported data
    op.execute('DELETE FROM `drop` WHERE rail_start_point_id IS NULL OR rail_end_point_id IS NULL')
    # Save existing correct data
    op.add_column('drop', sa.Column('start_point_id', sa.Integer(), nullable=False))
    op.add_column('drop', sa.Column('end_point_id', sa.Integer(), nullable=False))
    op.execute('UPDATE `drop` SET start_point_id=rail_start_point_id, end_point_id=rail_end_point_id')

    with op.batch_alter_table('drop') as batch_op:
        batch_op.create_foreign_key('fk__drop_point__end', 'points', ['end_point_id'], ['id'])
        batch_op.create_foreign_key('fk__drop_point__start', 'points', ['start_point_id'], ['id'])

        batch_op.drop_constraint(op.f('5'), 'foreignkey')
        batch_op.drop_constraint(op.f('6'), 'foreignkey')
        batch_op.drop_constraint(op.f('4'), 'foreignkey')
        batch_op.drop_constraint(op.f('3'), 'foreignkey')

        batch_op.create_unique_constraint('uk__fingerprint_new', ['start_point_id', 'end_point_id', 'container_id', 'company_id', 'effective_from', 'effective_to'])
        batch_op.drop_index(op.f('uk__fingerprint'))
        batch_op.create_unique_constraint('uk__fingerprint', ['start_point_id', 'end_point_id', 'container_id', 'company_id', 'effective_from', 'effective_to'])
        batch_op.drop_index(op.f('uk__fingerprint_new'))

        batch_op.drop_column('rail_start_point_id')
        batch_op.drop_column('rail_end_point_id')
        batch_op.drop_column('sea_start_point_id')
        batch_op.drop_column('sea_end_point_id')


def downgrade() -> None:
    """Downgrade schema."""
    # Save existing data
    op.add_column('drop', sa.Column('rail_end_point_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.add_column('drop', sa.Column('rail_start_point_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.execute('UPDATE `drop` SET rail_start_point_id=start_point_id, rail_end_point_id=end_point_id')

    with op.batch_alter_table('drop') as batch_op:
        batch_op.add_column(sa.Column('sea_end_point_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('sea_start_point_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
        batch_op.create_foreign_key(op.f('3'), 'points', ['rail_end_point_id'], ['id'])
        batch_op.create_foreign_key(op.f('4'), 'points', ['rail_start_point_id'], ['id'])
        batch_op.create_foreign_key(op.f('6'), 'points', ['sea_start_point_id'], ['id'])
        batch_op.create_foreign_key(op.f('5'), 'points', ['sea_end_point_id'], ['id'])

        batch_op.drop_constraint('fk__drop_point__start', type_='foreignkey')
        batch_op.drop_constraint('fk__drop_point__end', type_='foreignkey')

        batch_op.create_unique_constraint(op.f('uk__fingerprint_old'), ['sea_start_point_id', 'sea_end_point_id', 'rail_start_point_id', 'rail_end_point_id', 'container_id', 'company_id', 'effective_from', 'effective_to'])
        batch_op.drop_index('uk__fingerprint')
        batch_op.create_unique_constraint(op.f('uk__fingerprint'), ['sea_start_point_id', 'sea_end_point_id', 'rail_start_point_id', 'rail_end_point_id', 'container_id', 'company_id', 'effective_from', 'effective_to'])
        batch_op.drop_index('uk__fingerprint_old')

        batch_op.drop_column('end_point_id')
        batch_op.drop_column('start_point_id')
