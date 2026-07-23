import asyncio
import datetime
import json
import logging
from contextlib import suppress

from module_shared.redis_client import get_redis
from module_shared.repositories.locker import TaskAlreadyRunningError
from module_shared.repositories.locker.local_locker import LocalLocker
from pydantic import BaseModel

logger = logging.getLogger(__name__)

FESCO_POINTS_TODAY_TTL = 86400
FESCO_POINTS_OTHER_TTL = 43200
FESCO_ROUTES_TTL = 43200
FESCO_CONTAINERS_TTL = 86400


class CacheKeys:
    @staticmethod
    def get_departures_cache_key(date: datetime.date):
        return f"backend_user:fesco:departures:{date}"

    @staticmethod
    def get_destinations_cache_key(date: datetime.date, departure_point_id: str):
        return f"backend_user:fesco:destinations:{date}:{departure_point_id}"

    @staticmethod
    def get_wte_cache_key(date: datetime.date, departure_id: str, destination_id: str):
        return f"backend_user:fesco:containers:{date}:{departure_id}:{destination_id}"

    @staticmethod
    def get_routes_cache_key(date: datetime.date, departure_id: str, destination_id: str, wte_ids: list[str]):
        return f"backend_user:fesco:routes:{date}:{departure_id}:{destination_id}:{json.dumps(wte_ids, sort_keys=True)}"


def get_points_ttl(date: datetime.date) -> int:
    return FESCO_POINTS_TODAY_TTL if date == datetime.date.today() else FESCO_POINTS_OTHER_TTL


async def get_cached(cache_key: str, pydantic_class: type[BaseModel] | None = None):
    try:
        redis = get_redis()
        cached = await redis.get(cache_key)
        if cached is not None:
            raw_data = json.loads(cached)
            if not pydantic_class:
                return raw_data

            try:
                return [pydantic_class.model_validate(r) for r in raw_data]
            except Exception:
                logger.warning("Corrupt cache data for %s, re-fetching", cache_key, exc_info=True)
    except Exception:
        logger.warning("Redis unavailable for %s, falling back to API", cache_key, exc_info=True)


async def set_cache(key: str, data, ttl: int, model_dump: bool = False) -> bool:
    try:
        redis = get_redis()
        prepared_data = [r.model_dump(mode="json") for r in data] if model_dump else data
        await redis.set(key, json.dumps(prepared_data), ex=ttl)
        return True
    except Exception:
        logger.exception("Failed to set cache for %s", key)

    return False


@LocalLocker.locked(key=lambda key, *_, **__: key)
def set_cache_async(key: str, data, ttl: int, model_dump: bool = False):
    return asyncio.create_task(set_cache(key, data, ttl, model_dump))


def silent_set_cache_async(key: str, data, ttl: int, model_dump: bool = False):
    with suppress(TaskAlreadyRunningError):
        return set_cache_async(key, data, ttl, model_dump)
