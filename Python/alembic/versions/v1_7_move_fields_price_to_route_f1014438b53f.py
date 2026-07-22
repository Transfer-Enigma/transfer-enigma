"""v1.7-move-fields-price-to-route

Revision ID: f1014438b53f
Revises: 315657e09064
Create Date: 2026-04-07 23:57:19.462208

"""
from collections import defaultdict
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import and_

# revision identifiers, used by Alembic.
revision: str = 'f1014438b53f'
down_revision: Union[str, Sequence[str], None] = '315657e09064'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    routes = sa.Table('routes', sa.MetaData(), autoload_with=conn)
    prices = sa.Table('prices', sa.MetaData(), autoload_with=conn)

    op.add_column('routes', sa.Column('container_transfer_terms', mysql.ENUM('FIFO', 'FILO'), nullable=False, default='FILO'))
    op.add_column('routes', sa.Column('container_shipment_terms', mysql.ENUM('FOR'), nullable=False, default='FOR'))
    op.add_column('routes', sa.Column('container_owner', mysql.ENUM('COC', 'SOC'), nullable=False, default='COC'))

    # Swap routes constraint
    op.create_unique_constraint('uk__fingerprint_1', 'routes', ['company_id', 'start_point_id', 'end_point_id', 'effective_from', 'effective_to', 'container_shipment_terms', 'container_transfer_terms', 'container_owner'])
    op.drop_constraint('uk__fingerprint', 'routes', type_='unique')
    op.create_unique_constraint('uk__fingerprint', 'routes', ['company_id', 'start_point_id', 'end_point_id', 'effective_from', 'effective_to', 'container_shipment_terms', 'container_transfer_terms', 'container_owner'])
    op.drop_constraint('uk__fingerprint_1', 'routes', type_='unique')

    # Collect all price combinations
    distinct_combos = conn.execute(
        sa.select(
            prices.c.route_id,
            prices.c.container_owner,
            prices.c.container_transfer_terms,
            prices.c.container_shipment_terms
        ).distinct()
    ).fetchall()

    route_combos = defaultdict(list)
    for row in distinct_combos:
        route_combos[row.route_id].append(
            (row.container_owner, row.container_transfer_terms, row.container_shipment_terms)
        )

    # Duplicate routes
    for route_id, combos in route_combos.items():
        if len(combos) <= 1:
            continue

        # Grab original route row data
        original_route = conn.execute(routes.select().where(routes.c.id == route_id)).first()
        if not original_route:
            continue

        base_route_data = dict(original_route._mapping)
        base_route_data.pop('id', None)

        for owner, transfer, shipment in combos:
            new_route_data = base_route_data.copy()
            new_route_data.update({
                'container_owner': owner,
                'container_transfer_terms': transfer,
                'container_shipment_terms': shipment,
            })

            # insert new route
            res = conn.execute(routes.insert().values(new_route_data))
            new_route_id = res.inserted_primary_key[0]

            conn.execute(
                prices.update()
                .where(
                    and_(
                        prices.c.route_id == route_id,
                        prices.c.container_owner == owner,
                        prices.c.container_transfer_terms == transfer,
                        prices.c.container_shipment_terms == shipment,
                    ),
                )
                .values(route_id=new_route_id)
            )

    # Populate non-split routes with the single available combination
    op.execute("""
        UPDATE routes r
        JOIN (
            SELECT route_id,
                   MAX(container_owner) as co,
                   MAX(container_transfer_terms) as ct,
                   MAX(container_shipment_terms) as cs
            FROM prices
            GROUP BY route_id
        ) p ON r.id = p.route_id
        SET r.container_owner = p.co,
            r.container_transfer_terms = p.ct,
            r.container_shipment_terms = p.cs
    """)

    # Remove duplicate prices before applying the new shorter unique constraint
    op.execute("""
        DELETE p1 FROM prices p1
        INNER JOIN prices p2
          ON p1.route_id = p2.route_id AND p1.container_id = p2.container_id
        WHERE p1.id > p2.id
    """)

    # Swap prices constraint (temp -> drop old -> create new -> drop temp)
    op.create_unique_constraint('uk__fingerprint_1', 'prices', ['route_id', 'container_id'])
    op.drop_constraint('uk__fingerprint', 'prices', type_='unique')
    op.create_unique_constraint('uk__fingerprint', 'prices', ['route_id', 'container_id'])
    op.drop_constraint('uk__fingerprint_1', 'prices', type_='unique')

    op.drop_column('prices', 'container_owner')
    op.drop_column('prices', 'container_shipment_terms')
    op.drop_column('prices', 'container_transfer_terms')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('prices', sa.Column('container_transfer_terms', mysql.ENUM('FIFO', 'FILO'), nullable=False, default='FILO'))
    op.add_column('prices', sa.Column('container_shipment_terms', mysql.ENUM('FOR'), nullable=False, default='FOR'))
    op.add_column('prices', sa.Column('container_owner', mysql.ENUM('COC', 'SOC'), nullable=False, default='COC'))

    # Restore prices constraint
    op.create_unique_constraint('uk__fingerprint_1', 'prices', ['route_id', 'container_id', 'container_shipment_terms', 'container_transfer_terms', 'container_owner'])
    op.drop_constraint('uk__fingerprint', 'prices', type_='unique')
    op.create_unique_constraint('uk__fingerprint', 'prices', ['route_id', 'container_id', 'container_shipment_terms', 'container_transfer_terms', 'container_owner'])
    op.drop_constraint('uk__fingerprint_1', 'prices', type_='unique')

    # Copy data from routes to prices
    op.execute("""
        UPDATE prices p
        JOIN routes r ON p.route_id = r.id
        SET p.container_owner = r.container_owner,
            p.container_transfer_terms = r.container_transfer_terms,
            p.container_shipment_terms = r.container_shipment_terms
    """)

    # Redirect prices from duplicated routes to the master route (lowest ID)
    op.execute("""
        UPDATE prices p
        INNER JOIN (
            SELECT r1.id as dup_id, r2.id as master_id
            FROM routes r1
            INNER JOIN routes r2
              ON r1.company_id = r2.company_id
              AND r1.start_point_id = r2.start_point_id
              AND r1.end_point_id = r2.end_point_id
              AND r1.effective_from = r2.effective_from
              AND r1.effective_to = r2.effective_to
            WHERE r1.id > r2.id
        ) mapping ON p.route_id = mapping.dup_id
        SET p.route_id = mapping.master_id
    """)

    # Remove routes duplicated during upgrade
    op.execute("""
        DELETE r1 FROM routes r1
        INNER JOIN routes r2
          ON r1.company_id = r2.company_id
          AND r1.start_point_id = r2.start_point_id
          AND r1.end_point_id = r2.end_point_id
          AND r1.effective_from = r2.effective_from
          AND r1.effective_to = r2.effective_to
        WHERE r1.id > r2.id
    """)

    # Deduplicate prices against the restored extended fingerprint
    op.execute("""
        DELETE p1 FROM prices p1
        INNER JOIN prices p2
          ON p1.route_id = p2.route_id
          AND p1.container_id = p2.container_id
          AND p1.container_owner = p2.container_owner
          AND p1.container_transfer_terms = p2.container_transfer_terms
          AND p1.container_shipment_terms = p2.container_shipment_terms
        WHERE p1.id > p2.id
    """)

    # Restore routes constraint
    op.create_unique_constraint('uk__fingerprint_1', 'routes', ['company_id', 'start_point_id', 'end_point_id', 'effective_from', 'effective_to'])
    op.drop_constraint('uk__fingerprint', 'routes', type_='unique')
    op.create_unique_constraint('uk__fingerprint', 'routes', ['company_id', 'start_point_id', 'end_point_id', 'effective_from', 'effective_to'])
    op.drop_constraint('uk__fingerprint_1', 'routes', type_='unique')

    op.drop_column('routes', 'container_owner')
    op.drop_column('routes', 'container_shipment_terms')
    op.drop_column('routes', 'container_transfer_terms')
