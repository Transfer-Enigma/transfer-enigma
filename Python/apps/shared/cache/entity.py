from enum import StrEnum


class CacheEntity(StrEnum):
    """Entities that can be cached.

    A cache policy may only reference an entity listed here, so a policy
    row with an unknown entity is ignored instead of silently doing
    nothing.
    """

    DEPARTURES = "departures"
    DESTINATIONS = "destinations"
    CONTAINERS = "containers"
    ROUTES = "routes"
    POINTS = "points"
    RATES = "rates"
    SETTINGS = "settings"


# Entities that can be cached under multiple sources (e.g. FESCO departures
# and internal departures). For these entities source is required in a policy.
# All other entities are single-source: the entity itself identifies the
# source, so source is None in their policy.
MULTI_SOURCE_ENTITIES: frozenset[CacheEntity] = frozenset(
    {
        CacheEntity.DEPARTURES,
        CacheEntity.DESTINATIONS,
        CacheEntity.CONTAINERS,
        CacheEntity.ROUTES,
        CacheEntity.POINTS,
    }
)


def is_multi_source(entity: CacheEntity) -> bool:
    """Whether the entity requires an explicit source in its policy."""
    return entity in MULTI_SOURCE_ENTITIES
