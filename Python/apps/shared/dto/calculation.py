import datetime

from pydantic import BaseModel


class CalculationRequest(BaseModel):
    """What the caller asks to calculate.

    The API turns its own request model into this one, so the service does
    not depend on the shape of the API.
    """

    dispatch_date: datetime.date
    departure_internal_ids: list[int]
    destination_internal_ids: list[int]
    departure_external_ids: list[str]
    destination_external_ids: list[str]
    cargo_weight: float
    container_type: int
    head_truck: bool = False
    tail_truck: bool = False
