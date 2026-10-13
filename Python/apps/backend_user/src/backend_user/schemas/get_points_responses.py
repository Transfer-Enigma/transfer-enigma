from pydantic import BaseModel, ConfigDict

from .errors import RouteError


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | str  # noqa: A003
    name: str


class TranslationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    country: str


class PortTranslationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str


class GroupedPortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ids: list[int]
    external_ids: list[str]
    companies: list[CompanyResponse]
    translates: dict[str, PortTranslationResponse | None]


class GroupedPointWithPortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ids: list[int]
    external_ids: list[str]
    companies: list[CompanyResponse]
    translates: dict[str, TranslationResponse]
    ports: list[GroupedPortResponse]


class PointsDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    errors: list[RouteError]
    data: list[GroupedPointWithPortResponse]
