from abc import ABC
from typing import Any, ClassVar

from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class FilterDef:
    """Defines a list filter for a CRUD entity.

    Attributes:
        param: Query parameter name (from API request).
        model_field: SQLAlchemy model attribute name.
        operator: Comparison operator — "eq", "like", "gte", "lte".
    """

    def __init__(self, param: str, model_field: str, operator: str = "eq") -> None:
        self.param = param
        self.model_field = model_field
        self.operator = operator


class CRUDBase(ABC):
    """Generic CRUD template for admin data browser.

    Subclasses set ClassVar attributes and optionally override methods.
    """

    model: ClassVar[type]
    create_schema: ClassVar[type[BaseModel]]
    update_schema: ClassVar[type[BaseModel]]
    patch_schema: ClassVar[type[BaseModel]]
    response_schema: ClassVar[type[BaseModel]]
    list_response_schema: ClassVar[type[BaseModel] | None] = None
    list_filters: ClassVar[list[FilterDef]] = []

    async def list(  # noqa: A003
        self, session: AsyncSession, **filters: Any
    ) -> list[BaseModel]:
        stmt = select(self.model)
        stmt = self._apply_list_filters(stmt, **filters)
        result = await session.execute(stmt.order_by(self.model.id))  # type: ignore[attr-defined]
        schema = self.list_response_schema or self.response_schema
        return [schema.from_model(m) for m in result.scalars()]

    async def get(self, session: AsyncSession, id: int) -> BaseModel:  # noqa: A002
        model = await self._get_or_404(session, id)
        return self.response_schema.from_model(model)

    async def create(self, session: AsyncSession, data: BaseModel) -> BaseModel:
        model = self._build_instance(data)
        session.add(model)
        await session.flush()
        await session.refresh(model)
        return self.response_schema.from_model(model)

    async def update(self, session: AsyncSession, id: int, data: BaseModel) -> BaseModel:  # noqa: A002
        model = await self._get_or_404(session, id)
        self._apply_update(model, data)
        await session.flush()
        await session.refresh(model)
        return self.response_schema.from_model(model)

    async def patch(self, session: AsyncSession, id: int, data: BaseModel) -> BaseModel:  # noqa: A002
        model = await self._get_or_404(session, id)
        self._apply_patch(model, data)
        await session.flush()
        await session.refresh(model)
        return self.response_schema.from_model(model)

    async def delete(self, session: AsyncSession, id: int) -> None:  # noqa: A002
        model = await self._get_or_404(session, id)
        await session.delete(model)

    async def _get_or_404(self, session: AsyncSession, id: int) -> Any:  # noqa: A002
        model = await session.get(self.model, id)
        if not model:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} not found",
            )
        return model

    def _build_instance(self, data: BaseModel) -> Any:
        return self.model(**data.model_dump())

    def _apply_update(self, model: Any, data: BaseModel) -> None:
        for key, value in data.model_dump().items():
            setattr(model, key, value)

    def _apply_patch(self, model: Any, data: BaseModel) -> None:
        data_dump = data.model_dump(exclude_unset=True)
        for key, value in data_dump.items():
            if value is not None:
                setattr(model, key, value)

    def _apply_list_filters(self, stmt: Any, **filters: Any) -> Any:
        for fd in self.list_filters:
            value = filters.get(fd.param)
            if value is not None and value != "":
                col = getattr(self.model, fd.model_field)
                if fd.operator == "eq":
                    stmt = stmt.where(col == value)
                elif fd.operator == "like":
                    stmt = stmt.where(col.like(f"%{value}%"))
                elif fd.operator == "gte":
                    stmt = stmt.where(col >= value)
                elif fd.operator == "lte":
                    stmt = stmt.where(col <= value)
        return stmt
