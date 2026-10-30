"""Cache policy data layer.

Creates default cache policies that are still missing.
Existing rows are never touched.
"""

import logging

from shared.database import Base, get_database
from shared.dto.cache import CacheEntity
from shared.orm.cache_policy import CachePolicyModel
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Entities that can be cached under multiple sources (e.g. FESCO departures
# and internal departures). For these entities source is required in a policy.
# All other entities are single-source: the entity itself identifies the
# source, so source is None in their policy.
MULTI_SOURCE_ENTITIES: frozenset[CacheEntity] = frozenset(
    {
        CacheEntity.CONTAINERS,
        CacheEntity.CONTAINERS_TODAY,
        CacheEntity.DEPARTURES,
        CacheEntity.DEPARTURES_TODAY,
        CacheEntity.DESTINATIONS,
        CacheEntity.DESTINATIONS_TODAY,
        CacheEntity.POINTS,
        CacheEntity.POINTS_TODAY,
        CacheEntity.ROUTES,
        CacheEntity.ROUTES_TODAY,
    }
)


def is_multi_source(entity: CacheEntity) -> bool:
    """Whether the entity requires an explicit source in its policy."""
    return entity in MULTI_SOURCE_ENTITIES


# All supported (source, entity) combinations for cache policies.
_DEFAULT_CACHE_POLICIES: list[tuple[str | None, CacheEntity, bool, int, str]] = [
    # Single-source entities.
    (None, CacheEntity.RATES, True, 3600, "Currency rates from the CBR API"),
    (None, CacheEntity.SETTINGS, False, 3600, "Application settings"),
    # Multi-source entities: FESCO (external) + internal (database).
    ("fesco", CacheEntity.CONTAINERS_TODAY, True, 86400, "FESCO containers for today"),
    ("fesco", CacheEntity.CONTAINERS, True, 86400, "FESCO containers"),
    ("fesco", CacheEntity.DEPARTURES, True, 43200, "FESCO departure points"),
    ("fesco", CacheEntity.DEPARTURES_TODAY, True, 86400, "FESCO departure points for today"),
    ("fesco", CacheEntity.DESTINATIONS, True, 43200, "FESCO destination points"),
    ("fesco", CacheEntity.DESTINATIONS_TODAY, True, 86400, "FESCO destination points for today"),
    ("fesco", CacheEntity.POINTS, True, 86400, "FESCO points"),
    ("fesco", CacheEntity.POINTS_TODAY, True, 86400, "FESCO points for today"),
    ("fesco", CacheEntity.ROUTES, True, 43200, "FESCO routes"),
    ("fesco", CacheEntity.ROUTES_TODAY, True, 43200, "FESCO routes for today"),
    ("internal", CacheEntity.CONTAINERS, False, 86400, "Internal containers"),
    ("internal", CacheEntity.CONTAINERS_TODAY, False, 86400, "Internal containers for today"),
    ("internal", CacheEntity.DEPARTURES, False, 86400, "Internal departure points"),
    ("internal", CacheEntity.DEPARTURES_TODAY, False, 86400, "Internal departure points for today"),
    ("internal", CacheEntity.DESTINATIONS, False, 86400, "Internal destination points"),
    ("internal", CacheEntity.DESTINATIONS_TODAY, False, 86400, "Internal destination points for today"),
    ("internal", CacheEntity.POINTS, False, 86400, "Internal points"),
    ("internal", CacheEntity.POINTS_TODAY, False, 86400, "Internal points for today"),
    ("internal", CacheEntity.ROUTES, False, 86400, "Internal routes"),
    ("internal", CacheEntity.ROUTES_TODAY, False, 43200, "Internal routes for today"),
]


async def ensure_cache_policies() -> None:
    """Create cache policies that are still missing.

    Existing rows are left untouched: policies are admin-managed,
    the seeder only fills the gaps. Idempotent.
    """
    async with get_database().session_context() as session:
        conn = await session.connection()
        await conn.run_sync(Base.metadata.create_all)
        for source, entity, enabled, ttl, _description in _DEFAULT_CACHE_POLICIES:
            result = await session.execute(
                select(CachePolicyModel).where(
                    CachePolicyModel.source == source,
                    CachePolicyModel.entity == entity,
                ),
            )
            if result.scalar_one_or_none() is not None:
                continue
            session.add(
                CachePolicyModel(
                    source=source,
                    entity=entity,
                    enabled=enabled,
                    ttl=ttl,
                ),
            )
            await session.flush()
            logger.info(
                "Created default cache policy: %s:%s enabled=%s ttl=%s",
                source,
                entity,
                enabled,
                ttl,
            )
