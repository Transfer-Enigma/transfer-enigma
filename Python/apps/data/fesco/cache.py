import datetime
import json

from data.cache.entity import CacheEntity
from services.cache.backend import CacheBackend
from services.cache.registry import get_cache_registry

# The FESCO API is a data source of its own.
FESCO_SOURCE = "fesco"


def get_backend(entity: CacheEntity) -> CacheBackend:
    """The cache backend of the FESCO source for the given entity."""
    return get_cache_registry().backend(entity, source=FESCO_SOURCE)


def _today_or_base(today_entity: CacheEntity, base_entity: CacheEntity) -> CacheBackend:
    """Today backend if it is enabled, otherwise the base one.

    A missing or disabled today-policy falls back to the base policy, so
    to turn caching off entirely, disable the base policy.
    """
    backend = get_backend(today_entity)
    if backend.is_enabled():
        return backend
    return get_backend(base_entity)


def get_routes_backend(date: datetime.date) -> CacheBackend:
    """Routes backend that uses a longer TTL policy for today's date."""
    if date == datetime.date.today():
        return _today_or_base(CacheEntity.ROUTES_TODAY, CacheEntity.ROUTES)
    return get_backend(CacheEntity.ROUTES)


def get_containers_backend(date: datetime.date) -> CacheBackend:
    """Containers backend that uses a longer TTL policy for today's date."""
    if date == datetime.date.today():
        return _today_or_base(CacheEntity.CONTAINERS_TODAY, CacheEntity.CONTAINERS)
    return get_backend(CacheEntity.CONTAINERS)


def get_departures_backend(date: datetime.date) -> CacheBackend:
    """Departures backend that uses a longer TTL policy for today's date."""
    if date == datetime.date.today():
        return _today_or_base(CacheEntity.DEPARTURES_TODAY, CacheEntity.DEPARTURES)
    return get_backend(CacheEntity.DEPARTURES)


def get_destinations_backend(date: datetime.date) -> CacheBackend:
    """Destinations backend that uses a longer TTL policy for today's date."""
    if date == datetime.date.today():
        return _today_or_base(CacheEntity.DESTINATIONS_TODAY, CacheEntity.DESTINATIONS)
    return get_backend(CacheEntity.DESTINATIONS)


def departures_parts(date: datetime.date) -> tuple[str, ...]:
    return (date.isoformat(),)


def destinations_parts(date: datetime.date, departure_point_id: str) -> tuple[str, ...]:
    return date.isoformat(), departure_point_id


def containers_parts(date: datetime.date, departure_id: str, destination_id: str) -> tuple[str, ...]:
    return date.isoformat(), departure_id, destination_id


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
