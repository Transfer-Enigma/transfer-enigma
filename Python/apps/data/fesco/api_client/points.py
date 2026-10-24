import datetime

import aiohttp
from shared.cache import CacheEntity
from shared.config import get_settings

from ..cache import departures_parts, destinations_parts, get_backend, get_points_ttl


async def get_departure_points_by_date(date: datetime.date):
    backend = get_backend(CacheEntity.DEPARTURES)
    parts = departures_parts(date)

    cached_data = await backend.get(*parts)
    if cached_data:
        return cached_data

    data = await _fetch_departure_points_by_date(date)
    backend.silent_set_async(*parts, data=data, ttl=get_points_ttl(date))
    return data


async def _fetch_departure_points_by_date(date: datetime.date):
    async with aiohttp.ClientSession() as session:
        resp = await session.get(
            f"https://api.fesco.com/api/v1/lk/calc/fit/from?date={date.isoformat()}",
            headers={
                "Authorization": f"Bearer {get_settings().FESCO_API_KEY}",
                "X-Lk-Lang": "RU",
            },
        )
        resp.raise_for_status()
        data_from = await resp.json()
    return data_from.get("data")


async def get_destination_points_by_date(date: datetime.date, departure_point_id: str):
    backend = get_backend(CacheEntity.DESTINATIONS)
    parts = destinations_parts(date, departure_point_id)

    cached_data = await backend.get(*parts)
    if cached_data:
        return cached_data

    data = await _fetch_departure_points_by_date(date)
    backend.silent_set_async(*parts, data=data, ttl=get_points_ttl(date))
    return data


async def _fetch_destination_points_by_date(date: datetime.date, departure_point_id: str):
    async with aiohttp.ClientSession() as session:
        resp = await session.get(
            f"https://api.fesco.com/api/v1/lk/calc/fit/to"
            f"?date={date.isoformat()}&from={departure_point_id}",
            headers={
                "Authorization": f"Bearer {get_settings().FESCO_API_KEY}",
                "X-Lk-Lang": "RU",
            },
        )
        resp.raise_for_status()
        data_to = await resp.json()
    return data_to.get("data")
