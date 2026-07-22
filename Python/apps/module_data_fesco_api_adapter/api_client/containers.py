import asyncio
import datetime
import json
import logging

import aiohttp
from module_shared.config import get_settings
from module_shared.models.route import ContainerItem
from module_shared.redis_client import get_redis

from ..cache import FESCO_CONTAINERS_TTL, set_cache
from .transformers.containers import transform_containers

logger = logging.getLogger(__name__)


async def get_containers(date: datetime.date, departure_id: str, destination_id: str):
    cache_key = f"backend_user:fesco:containers:{date}:{departure_id}:{destination_id}"
    try:
        redis = get_redis()
        cached = await redis.get(cache_key)
        if cached is not None:
            raw = json.loads(cached)
            return [ContainerItem.model_validate(c) for c in raw]
    except Exception:
        logger.warning("Redis unavailable for containers, falling back to API")

    containers = await _fetch_containers(date, departure_id, destination_id)
    asyncio.create_task(set_cache(
        cache_key,
        [c.model_dump(mode="json") for c in containers],
        FESCO_CONTAINERS_TTL,
    ))
    return containers


async def _fetch_containers(date: datetime.date, departure_id: str, destination_id: str):
    async with aiohttp.ClientSession() as session:
        resp = await session.get(
            "https://my.fesco.com/api/v2/lk/offers/fit/wte?date={}&from={}&to={}".format(
                date.isoformat(),
                departure_id,
                destination_id,
            ),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {get_settings().FESCO_API_KEY}",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                "X-Lk-Lang": "RU",
            },
        )
        resp.raise_for_status()
        data_to = await resp.json()

    return transform_containers(data_to.get("data"))


def search_container_ids(containers: list, weight: int, container_type: int):
    needle = []

    for container in containers:
        if container.size == container_type:
            if container.weight_to:
                if container.weight_from <= weight <= container.weight_to:
                    needle.append(container.id)
            else:
                needle.append(container.id)

    return needle
