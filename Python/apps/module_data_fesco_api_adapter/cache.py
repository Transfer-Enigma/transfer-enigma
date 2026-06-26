import asyncio
import datetime
import json
import logging

from module_shared.models.route import Route
from module_shared.redis_client import get_redis

logger = logging.getLogger(__name__)

FESCO_POINTS_TODAY_TTL = 86400
FESCO_POINTS_OTHER_TTL = 43200
FESCO_ROUTES_TTL = 43200
FESCO_CONTAINERS_TTL = 86400


def _points_ttl(date: datetime.date) -> int:
    return FESCO_POINTS_TODAY_TTL if date == datetime.date.today() else FESCO_POINTS_OTHER_TTL


async def get_fesco_points_cached(cache_key: str, date: datetime.date, fetch_and_transform):
    try:
        redis = get_redis()
        cached = await redis.get(cache_key)
        if cached is not None:
            return json.loads(cached)
    except Exception:
        logger.warning("Redis unavailable for points, falling back to API")

    data = await fetch_and_transform()

    ttl = _points_ttl(date)
    asyncio.create_task(_set_json_async(cache_key, data, ttl))

    return data


async def get_fesco_routes_cached(cache_key: str, fetch):
    try:
        redis = get_redis()
        cached = await redis.get(cache_key)
        if cached is not None:
            try:
                return [Route.model_validate(r) for r in json.loads(cached)]
            except Exception:
                logger.warning("Corrupt cache data for %s, re-fetching", cache_key)
    except Exception:
        logger.warning("Redis unavailable for routes, falling back to API")

    data = await fetch()
    data = list(data)

    asyncio.create_task(_set_json_async(
        cache_key,
        [r.model_dump(mode="json") for r in data],
        FESCO_ROUTES_TTL,
    ))

    return data


async def _set_json_async(key: str, data, ttl: int) -> None:
    try:
        redis = get_redis()
        await redis.set(key, json.dumps(data, default=str), ex=ttl)
    except Exception:
        logger.exception("Failed to set cache for %s", key)
