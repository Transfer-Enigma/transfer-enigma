from pydantic import BaseModel, ConfigDict, Field, model_validator
from shared.cache import CacheEntity, is_multi_source
from shared.orm.cache_policy import CachePolicyModel
from shared.orm.company import CompanyModel
from shared.orm.setting import SettingModel

# ─── Companies ────────────────────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    name: str


class CompanyPatch(BaseModel):
    name: str | None = None


class CompanyResponse(BaseModel):
    id: int  # noqa: A003
    name: str

    @classmethod
    def from_model(cls, model: CompanyModel) -> CompanyModel:
        return cls(id=model.id, name=model.name)


class CompanyListResponse(BaseModel):
    id: int  # noqa: A003
    name: str


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
    RU_city: str | None = None
    RU_country: str | None = None

    @classmethod
    def from_model(cls, model: CompanyModel) -> PointResponse:
        return cls(
            id=model.id,
            city=model.city,
            country=model.country,
            RU_city=model.RU_city,
            RU_country=model.RU_country,
        )


class PointListResponse(BaseModel):
    id: int  # noqa: A003
    city: str
    country: str
    RU_city: str | None = None
    RU_country: str | None = None


# ─── Containers ───────────────────────────────────────────────────────────────

class ContainerCreate(BaseModel):
    size: int
    type: str  # noqa: A003
    weight_from: int
    weight_to: int
    name: str


class ContainerPatch(BaseModel):
    size: int | None = None
    type: str | None = None
    weight_from: int | None = None
    weight_to: int | None = None
    name: str | None = None


class ContainerResponse(BaseModel):
    id: int  # noqa: A003
    size: int
    type: str  # noqa: A003
    weight_from: int
    weight_to: int
    name: str

    @classmethod
    def from_model(cls, model: CompanyModel) -> ContainerResponse:
        return cls(
            id=model.id,
            size=model.size,
            type=model.type,
            weight_from=model.weight_from,
            weight_to=model.weight_to,
            name=model.name,
        )


class ContainerListResponse(BaseModel):
    id: int  # noqa: A003
    size: int
    type: str  # noqa: A003
    weight_from: int
    weight_to: int
    name: str


# ─── Route Segments ───────────────────────────────────────────────────────────

class RouteSegmentCreate(BaseModel):
    route_id: int
    start_point_id: int
    end_point_id: int
    company_id: int
    container_owner: str | None = None
    container_type: str | None = None
    price: float
    currency: str
    conversation_percents: float = 0.0


class RouteSegmentPatch(BaseModel):
    start_point_id: int | None = None
    end_point_id: int | None = None
    company_id: int | None = None
    container_owner: str | None = None
    container_type: str | None = None
    price: float | None = None
    currency: str | None = None
    conversation_percents: float | None = None


class RouteSegmentResponse(BaseModel):
    id: int  # noqa: A003
    route_id: int
    start_point_id: int
    end_point_id: int
    company_id: int
    container_owner: str | None = None
    container_type: str | None = None
    price: float
    currency: str
    conversation_percents: float

    @classmethod
    def from_model(cls, model: CompanyModel) -> RouteSegmentResponse:
        return cls(
            id=model.id,
            route_id=model.route_id,
            start_point_id=model.start_point_id,
            end_point_id=model.end_point_id,
            company_id=model.company_id,
            container_owner=model.container_owner,
            container_type=model.container_type,
            price=model.price,
            currency=model.currency,
            conversation_percents=model.conversation_percents,
        )


class RouteSegmentListResponse(BaseModel):
    id: int  # noqa: A003
    route_id: int
    start_point_id: int
    end_point_id: int
    company_id: int
    container_owner: str | None = None
    container_type: str | None = None
    price: float
    currency: str
    conversation_percents: float


class RouteSegmentStatsResponse(BaseModel):
    total_segments: int
    by_type: dict[str, int]
    by_is_through: dict[str, int]
    by_container_owner: dict[str, int]
    top_companies: list[dict]


# ─── Services ─────────────────────────────────────────────────────────────────

class ServiceCreate(BaseModel):
    name: str
    internal_name: str | None = None
    description: str | None = None
    hint: str | None = None
    mandatory: bool = False
    default: bool = False


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
    internal_name: str | None = None
    description: str | None = None
    hint: str | None = None
    mandatory: bool
    default: bool

    @classmethod
    def from_model(cls, model: CompanyModel) -> ServiceResponse:
        return cls(
            id=model.id,
            name=model.name,
            internal_name=model.internal_name,
            description=model.description,
            hint=model.hint,
            mandatory=model.mandatory,
            default=model.default,
        )


class ServiceListResponse(BaseModel):
    id: int  # noqa: A003
    name: str
    internal_name: str | None = None
    description: str | None = None
    hint: str | None = None
    mandatory: bool
    default: bool


# ─── Drop-off ─────────────────────────────────────────────────────────────────

class DropOffCreate(BaseModel):
    container_id: int
    company_id: int
    dates: str
    price: float
    currency: str


class DropOffPatch(BaseModel):
    container_id: int | None = None
    company_id: int | None = None
    dates: str | None = None
    price: float | None = None
    currency: str | None = None


class DropOffResponse(BaseModel):
    id: int  # noqa: A003
    container_id: int
    company_id: int
    dates: str
    price: float
    currency: str

    @classmethod
    def from_model(cls, model: CompanyModel) -> DropOffResponse:
        return cls(
            id=model.id,
            container_id=model.container_id,
            company_id=model.company_id,
            dates=model.dates,
            price=model.price,
            currency=model.currency,
        )


class DropOffListResponse(BaseModel):
    id: int  # noqa: A003
    container_id: int
    company_id: int
    dates: str
    price: float
    currency: str


# ─── Settings ─────────────────────────────────────────────────────────────────

class SettingCreate(BaseModel):
    group: str
    name: str
    description: str | None = None
    value_type: str
    value: str | None = None
    locked: bool = False


class SettingPatch(BaseModel):
    value: str | None = None
    value_type: str | None = None
    locked: bool | None = None


class SettingResponse(BaseModel):
    id: int  # noqa: A003
    group: str
    name: str
    description: str | None = None
    value_type: str
    value: str | None = None
    locked: bool

    @classmethod
    def from_model(cls, model: SettingModel) -> SettingResponse:
        return cls(
            id=model.id,
            group=model.group,
            name=model.name,
            description=model.description,
            value_type=model.value_type,
            value=model.value,
            locked=model.locked,
        )


# ─── Cache Policies ───────────────────────────────────────────────────────────

class CachePolicyCreate(BaseModel):
    source: str | None = None
    entity: str
    enabled: bool = True
    ttl: int = Field(default=3600, ge=1)

    @model_validator(mode="after")
    def _validate_source(self) -> CachePolicyCreate:
        entity = CacheEntity(self.entity)
        if is_multi_source(entity) and not self.source:
            raise ValueError(f"Entity {self.entity} requires a source")
        if not is_multi_source(entity) and self.source:
            raise ValueError(f"Entity {self.entity} is single-source, source must be None")
        return self


class CachePolicyPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    ttl: int | None = Field(default=None, ge=1)


class CacheInvalidateResponse(BaseModel):
    deleted: int


class CachePolicyResponse(BaseModel):
    id: int  # noqa: A003
    source: str | None
    entity: str
    enabled: bool
    ttl: int

    @classmethod
    def from_model(cls, model: CachePolicyModel) -> CachePolicyResponse:
        return cls(
            id=model.id,
            source=model.source,
            entity=model.entity,
            enabled=model.enabled,
            ttl=model.ttl,
        )
