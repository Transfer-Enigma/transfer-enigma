import asyncio
import datetime
import json
from collections.abc import Iterable

import aiohttp
from backend_user.config import get_settings
from module_shared.models.route import Route

from ..cache import get_fesco_routes_cached
from .transformers.routes import transform_routes


async def find_all_paths(
    date: datetime.date,
    departure_id: str,
    destination_id: str,
    wte_ids: list[str],
    _: bool = False,
) -> Iterable[Route]:
    sorted_ids = json.dumps(wte_ids, sort_keys=True)
    cache_key = f"backend_user:fesco:routes:{date}:{departure_id}:{destination_id}:{sorted_ids}"
    return await get_fesco_routes_cached(
        cache_key,
        lambda: _fetch_all_paths(date, departure_id, destination_id, wte_ids),
    )


async def _fetch_all_paths(
    date: datetime.date,
    departure_id: str,
    destination_id: str,
    wte_ids: list[str],
) -> Iterable[Route]:
    async with aiohttp.ClientSession() as session:
        coroutines = [
            _get_routes(date, departure_id, destination_id, wte_id, session)
            for wte_id in wte_ids
        ]
        res = await asyncio.gather(*coroutines, return_exceptions=True)

    routes = []
    for routes_group in res:
        if not isinstance(routes_group, BaseException):
            routes.extend(routes_group)

    return transform_routes(routes)


async def _get_routes(
    date: datetime.date,
    departure_id: str,
    destination_id: str,
    wte_id: str,
    session,
):
    resp = await session.get(
        "https://my.fesco.com/api/v2/lk/offers/fit?date={}&from={}&to={}&wte={}&co=COC".format(
            date.isoformat(),
            departure_id,
            destination_id,
            wte_id,
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

    return (await resp.json()).get("data", [])
