import asyncio
import datetime
import json
import logging
from decimal import Decimal

from module_shared.database import get_database
from module_shared.redis_client import get_redis
from module_shared.schemas.rate import RateModel
from pycbrf.toolbox import ExchangeRates
from sqlalchemy import delete

logger = logging.getLogger(__name__)

RATES_CACHE_KEY = "backend_user:rates:latest"
RATES_CACHE_TTL = 86400


async def main():
    dt_now = datetime.datetime.now()
    today = dt_now.date()

    logger.info("Fetching rates from CBR for %s", today)

    try:
        rates_obj = await asyncio.to_thread(ExchangeRates, dt_now)
    except Exception:
        logger.exception("Failed to fetch rates from CBR API")
        raise

    rates = {currency.code: float(currency.value) for currency in rates_obj.rates}
    rates["RUB"] = 1.0
    rates["RUR"] = 1.0
    rates["РУБ"] = 1.0

    logger.info("Fetched %d rates from CBR", len(rates))

    db = get_database()
    async with db.session_context() as session:
        result = await session.execute(
            delete(RateModel).where(RateModel.date == today)
        )
        deleted = result.rowcount
        if deleted:
            logger.info("Deleted %d existing rate rows for %s", deleted, today)

        rows = [
            RateModel(code=code, rate=Decimal(str(rate)), date=today)
            for code, rate in rates.items()
        ]
        session.add_all(rows)
        await session.flush()

    logger.info("Inserted %d rate rows for %s", len(rows), today)

    try:
        redis = get_redis()
        payload = json.dumps({"rates": rates, "date": today.isoformat()})
        await redis.set(RATES_CACHE_KEY, payload, ex=RATES_CACHE_TTL)
        logger.info("Rates cached in Redis for %s", today)
    except Exception:
        logger.exception("Failed to cache rates in Redis")
