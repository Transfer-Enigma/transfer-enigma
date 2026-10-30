import datetime

from fastapi import APIRouter

from services.rates.get import get_rates as _get_rates

router = APIRouter(prefix="/v1/rates", tags=["v1", "rates"])


@router.get("")
async def get_rates(dt_now: datetime.datetime | None = None):
    rates, _ = await _get_rates(dt_now)
    return rates
