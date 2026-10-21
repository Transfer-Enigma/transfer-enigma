import datetime
import logging

import aiohttp
from shared.cache import CacheEntity
from shared.config import get_settings
from shared.dto.route import ContainerItem

from ..cache import containers_parts, get_backend
from .transformers.containers import transform_containers

logger = logging.getLogger(__name__)


async def get_containers(date: datetime.date, departure_id: str, destination_id: str):
    backend = get_backend()
    parts = containers_parts(date, departure_id, destination_id)

    cached_data = await backend.get(CacheEntity.CONTAINERS, *parts, model=ContainerItem)
    if cached_data:
        return cached_data

    containers = await _fetch_containers(date, departure_id, destination_id)
    backend.silent_set_async(CacheEntity.CONTAINERS, *parts, data=containers, dump=True)
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
