import datetime
import json

from data.cache.registry import get_cache_registry
from shared.cache import CacheBackend, CacheEntity

# The FESCO API is a data source of its own.
FESCO_SOURCE = "fesco"

# The points of today change less often than the points of the other days.
FESCO_POINTS_TODAY_TTL = 86400
FESCO_POINTS_OTHER_TTL = 43200


def get_backend(entity: CacheEntity) -> CacheBackend:
    """The cache backend of the FESCO source for the given entity."""
    return get_cache_registry().backend(entity, source=FESCO_SOURCE)


def departures_parts(date: datetime.date) -> tuple[str, ...]:
    return (date.isoformat(),)


def destinations_parts(date: datetime.date, departure_point_id: str) -> tuple[str, ...]:
    return (date.isoformat(), departure_point_id)


def containers_parts(date: datetime.date, departure_id: str, destination_id: str) -> tuple[str, ...]:
    return (date.isoformat(), departure_id, destination_id)


def routes_parts(
    date: datetime.date,
    departure_id: str,
    destination_id: str,
    wte_ids: list[str],
) -> tuple[str, ...]:
    return (
        date.isoformat(),
        departure_id,
        destination_id,
        json.dumps(wte_ids, sort_keys=True),
    )


def get_points_ttl(date: datetime.date) -> int:
    """TTL of the points, the policy provides the default one."""
    return FESCO_POINTS_TODAY_TTL if date == datetime.date.today() else FESCO_POINTS_OTHER_TTL
