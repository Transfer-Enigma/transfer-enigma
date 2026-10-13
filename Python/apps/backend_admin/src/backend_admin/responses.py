from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class DetailErrorResponse(BaseModel, Generic[T]):
    detail: T


class ErrorDescriptor(BaseModel):
    class_type: str
    description: str | None = None


class MultiErrorResponse(BaseModel):
    errors: list[ErrorDescriptor]
