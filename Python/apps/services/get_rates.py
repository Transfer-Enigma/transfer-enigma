import asyncio
import datetime
import logging

from data.cache.registry import get_cache_registry
from pycbrf.toolbox import ExchangeRates
from shared.cache import CacheEntity

logger = logging.getLogger(__name__)

CBR_SOURCE = "cbr"
RATES_CACHE_PART = "latest"


async def _set_rates_cache(rates: dict[str, float], dt: datetime.date) -> None:
    try:
        backend = get_cache_registry().backend(CBR_SOURCE)
        task = backend.silent_set_async(
            CacheEntity.RATES,
            RATES_CACHE_PART,
            data={"rates": rates, "date": dt.isoformat()},
            dump=True,
        )
        if task is not None:
            await task
        logger.info("Rates cached for %s", dt)
    except Exception:
        logger.exception("Failed to cache rates")


async def get_rates(dt_now: datetime.datetime | None = None) -> tuple[dict[str, float], datetime.date]:
    if dt_now is None:
        dt_now = datetime.datetime.now()

    today = dt_now.date()

    try:
        rates_obj = await asyncio.to_thread(ExchangeRates, dt_now)
        rates = {currency.code: float(currency.value) for currency in rates_obj.rates}
        rates["RUB"] = 1
        rates["RUR"] = 1
        rates["РУБ"] = 1

        asyncio.create_task(_set_rates_cache(rates, today))
        return rates, today
    except Exception:
        logger.warning("Failed to fetch rates from CBR API, trying cache fallback", exc_info=True)

    try:
        backend = get_cache_registry().backend(CBR_SOURCE)
        cached = await backend.get(CacheEntity.RATES, RATES_CACHE_PART)
        if cached is not None:
            cached_date = datetime.date.fromisoformat(cached["date"])
            logger.info("Returning cached rates from %s", cached_date)
            return cached["rates"], cached_date
    except Exception:
        logger.exception("Failed to read rates from cache fallback")

    msg = "No rates available from CBR API or cache"
    logger.error(msg)
    raise RuntimeError(msg)
