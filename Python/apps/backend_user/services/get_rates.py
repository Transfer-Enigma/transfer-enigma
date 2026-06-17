import datetime
import json
import logging
from decimal import Decimal

from module_shared.database import get_database
from module_shared.redis_client import get_redis
from module_shared.schemas.rate import RateModel
from sqlalchemy import func, select

logger = logging.getLogger(__name__)

RATES_CACHE_KEY = "backend_user:rates:latest"
RATES_CACHE_TTL = 86400


async def _get_rates_from_db() -> tuple[dict[str, float], datetime.date] | None:
    db = get_database()
    async with db.session_context() as session:
        latest_date = await session.scalar(select(func.max(RateModel.date)))
        if latest_date is None:
            return None

        result = await session.execute(
            select(RateModel.code, RateModel.rate).where(RateModel.date == latest_date)
        )
        rows = result.all()

    if not rows:
        return None

    rates: dict[str, float] = {}
    for row in rows:
        val = row.rate
        rates[row.code] = float(val) if isinstance(val, Decimal) else float(val)

    rates.setdefault("RUB", 1.0)
    rates.setdefault("RUR", 1.0)
    rates.setdefault("РУБ", 1.0)

    return rates, latest_date


async def _set_rates_cache(rates: dict[str, float], dt: datetime.date) -> None:
    try:
        redis = get_redis()
        payload = json.dumps({"rates": rates, "date": dt.isoformat()})
        await redis.set(RATES_CACHE_KEY, payload, ex=RATES_CACHE_TTL)
        logger.info("Rates cached in Redis for %s", dt)
    except Exception:
        logger.exception("Failed to cache rates in Redis")


async def get_rates(_dt_now: datetime.datetime | None = None) -> tuple[dict[str, float], datetime.date]:
    redis = get_redis()

    try:
        raw = await redis.get(RATES_CACHE_KEY)
        if raw is not None:
            payload = json.loads(raw)
            cached_date = datetime.date.fromisoformat(payload["date"])
            logger.debug("Returning cached rates from %s", cached_date)
            return payload["rates"], cached_date
    except Exception:
        logger.exception("Failed to read rates from Redis")

    db_result = await _get_rates_from_db()
    if db_result is not None:
        rates, rates_date = db_result
        await _set_rates_cache(rates, rates_date)
        return rates, rates_date

    msg = "No rates available from Redis or database"
    logger.error(msg)
    raise RuntimeError(msg)
