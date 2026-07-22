import datetime
import json
import logging

from module_shared.models.route import RouteResult
from module_shared.redis_client import get_redis

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
    def get_routes_cache_key(date: datetime.date, departure_id: str, destination_id: str, wte_ids: list[str]):
        return f"backend_user:fesco:routes:{date}:{departure_id}:{destination_id}:{json.dumps(wte_ids, sort_keys=True)}"


def get_points_ttl(date: datetime.date) -> int:
    return FESCO_POINTS_TODAY_TTL if date == datetime.date.today() else FESCO_POINTS_OTHER_TTL


async def get_cached(cache_key: str):
    try:
        redis = get_redis()
        cached = await redis.get(cache_key)
        if cached is not None:
            return json.loads(cached)
    except Exception:
        logger.warning("Redis unavailable for %s, falling back to API", cache_key, exc_info=True)


async def get_fesco_routes_cached(cache_key: str):
    cached = await get_cached(cache_key)
    if cached is None:
        return None

    try:
        return [RouteResult.model_validate(r) for r in cached]
    except Exception:
        logger.warning("Corrupt cache data for %s, re-fetching", cache_key, exc_info=True)


async def set_cache(key: str, data, ttl: int) -> None:
    try:
        redis = get_redis()
        await redis.set(key, json.dumps(data), ex=ttl)
    except Exception:
        logger.exception("Failed to set cache for %s", key)
