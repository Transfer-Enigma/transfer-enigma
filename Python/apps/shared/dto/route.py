from datetime import datetime

from pydantic import BaseModel


class ContainerItem(BaseModel):
    id: int | str  # noqa: A003
    type: str  # noqa: A003
    size: int
    weight_from: float | int | None = None
    weight_to: float | int | None = None
    name: str = ""


class PriceItem(BaseModel):
    container: ContainerItem | None = None
    value: float
    currency: str
    conversation_percents: float = 0.0


class ServiceItem(BaseModel):
    segment_id: int | str
    name: str
    description: str
    hint: str | None = None
    currency: str | None = None
    price: float | None = None
    checked: bool = False
    mandatory: bool = False


class DropItem(BaseModel):
    price: float
    conversation_percents: float
    currency: str


class RouteSegment(BaseModel):
    id: int | str  # noqa: A003
    company: str | None
    type: str | None  # noqa: A003
    effectiveFrom: datetime | str
    effectiveTo: datetime | str
    startPointCountry: str
    startPointName: str
    endPointCountry: str
    endPointName: str
    comment: str | None = None
    timetable: str | None = None
    container_transfer_terms: str | None = None
    container_shipment_terms: str | None = None
    container_owner: str | None = None
    prices: list[PriceItem] = []


class RouteResult(BaseModel):
    segments: list[RouteSegment]
    drop: DropItem | None = None
    may_be_invalid: bool = False
    services: list[ServiceItem] = []
