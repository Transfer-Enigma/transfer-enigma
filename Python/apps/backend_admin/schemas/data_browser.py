from module_data_internal.schemas import (
    CompanyModel,
    ContainerModel,
    DropModel,
    PointModel,
    ServiceModel,
)
from module_data_internal.schemas.route import PriceModel, RouteModel, ServicePriceModel
from pydantic import BaseModel

# ─── Companies ────────────────────────────────────────────────────────────────


class CompanyCreate(BaseModel):
    name: str


class CompanyPatch(BaseModel):
    name: str | None = None


class CompanyResponse(BaseModel):
    id: int  # noqa: A003
    name: str

    @classmethod
    def from_model(cls, model: CompanyModel) -> "CompanyResponse":
        return cls(id=model.id, name=model.name)


# ─── Points ───────────────────────────────────────────────────────────────────


class PointCreate(BaseModel):
    city: str
    country: str
    RU_city: str | None = None
    RU_country: str | None = None


class PointPatch(BaseModel):
    city: str | None = None
    country: str | None = None
    RU_city: str | None = None
    RU_country: str | None = None


class PointResponse(BaseModel):
    id: int  # noqa: A003
    city: str
    country: str
    RU_city: str | None
    RU_country: str | None

    @classmethod
    def from_model(cls, model: PointModel) -> "PointResponse":
        return cls(
            id=model.id,
            city=model.city,
            country=model.country,
            RU_city=model.RU_city,
            RU_country=model.RU_country,
        )


# ─── Containers ───────────────────────────────────────────────────────────────


class ContainerCreate(BaseModel):
    size: int
    weight_from: float
    weight_to: float
    name: str
    type: str  # noqa: A003  # "DC" or "HC"


class ContainerPatch(BaseModel):
    size: int | None = None
    weight_from: float | None = None
    weight_to: float | None = None
    name: str | None = None
    type: str | None = None  # noqa: A003


class ContainerResponse(BaseModel):
    id: int  # noqa: A003
    size: int
    weight_from: float
    weight_to: float
    name: str
    type: str  # noqa: A003

    @classmethod
    def from_model(cls, model: ContainerModel) -> "ContainerResponse":
        return cls(
            id=model.id,
            size=model.size,
            weight_from=model.weight_from,
            weight_to=model.weight_to,
            name=model.name,
            type=model.type.value,
        )


# ─── Route Segments (composite) ────────────────────────────────────────────────


class PricePayload(BaseModel):
    container_id: int
    value: float | None = None
    currency: str
    conversation_percents: float = 0


class ServicePricePayload(BaseModel):
    service_id: int
    container_id: int | None = None
    currency: str
    price: float


class PriceResponse(BaseModel):
    id: int  # noqa: A003
    container_id: int
    value: float | None
    currency: str
    conversation_percents: float

    @classmethod
    def from_model(cls, model: PriceModel) -> "PriceResponse":
        return cls(
            id=model.id,
            container_id=model.container_id,
            value=model.value,
            currency=model.currency,
            conversation_percents=model.conversation_percents,
        )


class ServicePriceResponse(BaseModel):
    id: int  # noqa: A003
    service_id: int
    container_id: int | None
    currency: str
    price: float

    @classmethod
    def from_model(cls, model: ServicePriceModel) -> "ServicePriceResponse":
        return cls(
            id=model.id,
            service_id=model.service_id,
            container_id=model.container_id,
            currency=model.currency,
            price=model.price,
        )


class RouteSegmentCreate(BaseModel):
    company_id: int
    start_point_id: int
    end_point_id: int
    dropp_off_point_id: int | None = None
    effective_from: str  # YYYY-MM-DD
    effective_to: str  # YYYY-MM-DD
    comment: str | None = None
    timetable: str | None = None
    is_through: bool = True
    type: str  # noqa: A003  # "SEA" or "RAIL"
    container_transfer_terms: str  # FIFO, FILO, LIFO, LILO
    container_shipment_terms: str  # FOR, FOB, FCA
    container_owner: str  # COC, SOC
    prices: list[PricePayload] = []
    services: list[ServicePricePayload] = []


class RouteSegmentPatch(BaseModel):
    company_id: int | None = None
    start_point_id: int | None = None
    end_point_id: int | None = None
    dropp_off_point_id: int | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    comment: str | None = None
    timetable: str | None = None
    is_through: bool | None = None
    type: str | None = None  # noqa: A003
    container_transfer_terms: str | None = None
    container_shipment_terms: str | None = None
    container_owner: str | None = None


class RouteSegmentListResponse(BaseModel):
    id: int  # noqa: A003
    company_id: int
    start_point_id: int
    end_point_id: int
    type: str  # noqa: A003
    effective_from: str
    effective_to: str

    @classmethod
    def from_model(cls, model: RouteModel) -> "RouteSegmentListResponse":
        return cls(
            id=model.id,
            company_id=model.company_id,
            start_point_id=model.start_point_id,
            end_point_id=model.end_point_id,
            type=model.type.value,
            effective_from=model.effective_from.isoformat(),
            effective_to=model.effective_to.isoformat(),
        )


class RouteSegmentResponse(BaseModel):
    id: int  # noqa: A003
    company_id: int
    start_point_id: int
    end_point_id: int
    dropp_off_point_id: int | None
    effective_from: str
    effective_to: str
    comment: str | None
    timetable: str | None
    is_through: bool
    type: str  # noqa: A003
    container_transfer_terms: str
    container_shipment_terms: str
    container_owner: str
    prices: list[PriceResponse]
    services: list[ServicePriceResponse]

    @classmethod
    def from_model(cls, model: RouteModel) -> "RouteSegmentResponse":
        return cls(
            id=model.id,
            company_id=model.company_id,
            start_point_id=model.start_point_id,
            end_point_id=model.end_point_id,
            dropp_off_point_id=model.dropp_off_point_id,
            effective_from=model.effective_from.isoformat(),
            effective_to=model.effective_to.isoformat(),
            comment=model.comment,
            timetable=model.timetable,
            is_through=model.is_through,
            type=model.type.value,
            container_transfer_terms=model.container_transfer_terms.value,
            container_shipment_terms=model.container_shipment_terms.value,
            container_owner=model.container_owner.value,
            prices=[PriceResponse.from_model(p) for p in model.prices],
            services=[ServicePriceResponse.from_model(s) for s in model.services],
        )


# ─── Services ─────────────────────────────────────────────────────────────────


class ServiceCreate(BaseModel):
    name: str
    internal_name: str
    description: str
    hint: str | None = None
    mandatory: bool = False
    default: bool = True


class ServicePatch(BaseModel):
    name: str | None = None
    internal_name: str | None = None
    description: str | None = None
    hint: str | None = None
    mandatory: bool | None = None
    default: bool | None = None


class ServiceResponse(BaseModel):
    id: int  # noqa: A003
    name: str
    internal_name: str
    description: str
    hint: str | None
    mandatory: bool
    default: bool

    @classmethod
    def from_model(cls, model: ServiceModel) -> "ServiceResponse":
        return cls(
            id=model.id,
            name=model.name,
            internal_name=model.internal_name,
            description=model.description,
            hint=model.hint,
            mandatory=model.mandatory,
            default=model.default,
        )


# ─── Drop-off ─────────────────────────────────────────────────────────────────


class DropOffCreate(BaseModel):
    container_id: int
    company_id: int
    start_point_id: int | None = None
    end_point_id: int | None = None
    effective_from: str  # YYYY-MM-DD
    effective_to: str  # YYYY-MM-DD
    price: float = 0
    conversation_percents: float = 0
    currency: str


class DropOffPatch(BaseModel):
    container_id: int | None = None
    company_id: int | None = None
    start_point_id: int | None = None
    end_point_id: int | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    price: float | None = None
    conversation_percents: float | None = None
    currency: str | None = None


class DropOffResponse(BaseModel):
    id: int  # noqa: A003
    container_id: int
    company_id: int
    start_point_id: int | None
    end_point_id: int | None
    effective_from: str
    effective_to: str
    price: float
    conversation_percents: float
    currency: str

    @classmethod
    def from_model(cls, model: DropModel) -> "DropOffResponse":
        return cls(
            id=model.id,
            container_id=model.container_id,
            company_id=model.company_id,
            start_point_id=model.start_point_id,
            end_point_id=model.end_point_id,
            effective_from=model.effective_from.isoformat(),
            effective_to=model.effective_to.isoformat(),
            price=model.price,
            conversation_percents=model.conversation_percents,
            currency=model.currency,
        )
