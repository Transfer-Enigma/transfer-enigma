from dataclasses import dataclass
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
    ROUTES_TODAY = "routes_today"
    CONTAINERS_TODAY = "containers_today"
    DEPARTURES_TODAY = "departures_today"
    DESTINATIONS_TODAY = "destinations_today"
    POINTS_TODAY = "points_today"


@dataclass(frozen=True)
class CachePolicy:
    """Caching configuration of one entity of one source.

    It mirrors one row of the cache_policies table: an entity is only
    cached when a policy for it exists and is enabled.

    For multi-source entities (see cache_policies.MULTI_SOURCE_ENTITIES) source is
    required and identifies which provider the data comes from. For
    single-source entities (e.g. rates from CBR, settings from the internal
    DB) source is None — the entity itself identifies the source.
    """

    source: str | None
    entity: CacheEntity
    enabled: bool
    ttl: int
