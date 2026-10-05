from module_shared.models.route import RouteResult
from pydantic import BaseModel, Field


class CollectionItem(BaseModel):
    segments: list[int] = Field(min_length=1)
    services: list[int] = Field(default_factory=list)


class CreateCollectionRequest(BaseModel):
    items: list[CollectionItem] = Field(min_length=1, max_length=50)


class CreatedCollectionResponse(BaseModel):
    uid: str


class CollectionResponse(BaseModel):
    uid: str
    routes: list[RouteResult]
