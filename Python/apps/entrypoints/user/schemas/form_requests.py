import datetime

from pydantic import BaseModel
from shared.dto.calculation import CalculationRequest


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

    def to_calculation_request(self) -> CalculationRequest:
        """The request of the calculation service."""
        return CalculationRequest(
            dispatch_date=self.dispatchDate,
            departure_internal_ids=self.departureInternalIds,
            destination_internal_ids=self.destinationInternalIds,
            departure_external_ids=self.departureExternalIds,
            destination_external_ids=self.destinationExternalIds,
            cargo_weight=self.cargoWeight,
            container_type=self.containerType,
            head_truck=self.headTruck,
            tail_truck=self.tailTruck,
        )
