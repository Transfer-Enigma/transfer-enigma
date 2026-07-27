import datetime

from pydantic import BaseModel


class CalculateFormRequest(BaseModel):
    dispatchDate: datetime.date

    departureInternalIds: list[int]
    destinationInternalIds: list[int]
    departureExternalIds: list[str]
    destinationExternalIds: list[str]

    cargoWeight: float
    containerType: int

    headTruck: bool = False
    tailTruck: bool = False
