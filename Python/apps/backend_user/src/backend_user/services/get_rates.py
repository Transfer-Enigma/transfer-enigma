import asyncio
import datetime
import json
import logging

from module_shared.redis_client import get_redis
from pycbrf.toolbox import ExchangeRates

logger = logging.getLogger(__name__)

RATES_CACHE_KEY = "backend_user:rates:latest"
RATES_CACHE_TTL = 86400  # 24 hours


async def _set_rates_cache(rates: dict[str, float], dt: datetime.date) -> None:
    try:
        redis = get_redis()
        payload = json.dumps({"rates": rates, "date": dt.isoformat()})
        await redis.set(RATES_CACHE_KEY, payload, ex=RATES_CACHE_TTL)
        logger.info("Rates cached in Redis for %s", dt)
    except Exception:
        logger.exception("Failed to cache rates in Redis")


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
        logger.warning("Failed to fetch rates from CBR API, trying Redis fallback", exc_info=True)

    try:
        redis = get_redis()
        raw = await redis.get(RATES_CACHE_KEY)
        if raw is not None:
            payload = json.loads(raw)
            cached_date = datetime.date.fromisoformat(payload["date"])
            logger.info("Returning cached rates from %s", cached_date)
            return payload["rates"], cached_date
    except Exception:
        logger.exception("Failed to read rates from Redis fallback")

    msg = "No rates available from CBR API or Redis cache"
    logger.error(msg)
    raise RuntimeError(msg)
