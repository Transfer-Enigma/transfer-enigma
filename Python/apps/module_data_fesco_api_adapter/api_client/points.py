import datetime

import aiohttp
from module_shared.config import get_settings

from ..cache import CacheKeys, get_fesco_points_cached


async def get_departure_points_by_date(date: datetime.date):
    return await get_fesco_points_cached(
        CacheKeys.get_departures_cache_key(date),
        date,
        lambda: _fetch_departure_points_by_date(date),
    )


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
    return await get_fesco_points_cached(
        CacheKeys.get_destinations_cache_key(date, departure_point_id),
        date,
        lambda pid=departure_point_id: _fetch_destination_points_by_date(date, pid),
    )


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
