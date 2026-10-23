import datetime
import json

from data.cache.registry import get_cache_registry
from shared.cache import CacheBackend, CacheEntity

# The FESCO API is a data source of its own.
FESCO_SOURCE = "fesco"


def get_backend(entity: CacheEntity) -> CacheBackend:
    """The cache backend of the FESCO source for the given entity."""
    return get_cache_registry().backend(entity, source=FESCO_SOURCE)


def get_routes_backend(date: datetime.date) -> CacheBackend:
    """Routes backend that uses a longer TTL policy for today's date."""
    if date == datetime.date.today():
        return get_backend(CacheEntity.ROUTES_TODAY)
    return get_backend(CacheEntity.ROUTES)


def get_containers_backend(date: datetime.date) -> CacheBackend:
    """Containers backend that uses a longer TTL policy for today's date."""
    if date == datetime.date.today():
        return get_backend(CacheEntity.CONTAINERS_TODAY)
    return get_backend(CacheEntity.CONTAINERS)


def get_departures_backend(date: datetime.date) -> CacheBackend:
    if date == datetime.date.today():
        return get_backend(CacheEntity.DEPARTURES_TODAY)
    return get_backend(CacheEntity.DEPARTURES)


def get_destinations_backend(date: datetime.date) -> CacheBackend:
    if date == datetime.date.today():
        return get_backend(CacheEntity.DESTINATIONS_TODAY)
    return get_backend(CacheEntity.DESTINATIONS)


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
