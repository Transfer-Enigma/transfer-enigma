import datetime

from fastapi import APIRouter

from pydantic import BaseModel
from services.rates.get import get_rates as _get_rates

router = APIRouter(prefix="/v2/rates", tags=["v2", "rates"])


class GetRatesResponse(BaseModel):
    rates: dict[str, float]
    updated_at: datetime.date


@router.get("", response_model=GetRatesResponse)
async def get_rates(dt_now: datetime.datetime | None = None):
    rates, updated_at = await _get_rates(dt_now)
    return {"rates": rates, "updated_at": updated_at}
