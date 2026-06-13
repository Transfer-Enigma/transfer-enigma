import datetime
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND

from backend_admin.schemas.data_browser import (
    RouteSegmentCreate,
    RouteSegmentListResponse,
    RouteSegmentPatch,
    RouteSegmentResponse,
)
from backend_admin.service.crud_base import CRUDBase, FilterDef
from module_data_internal.schemas.route import (
    ContainerOwner,
    ContainerShipmentTerms,
    ContainerTransferTerms,
    PriceModel,
    RouteModel,
    RouteType,
    ServicePriceModel,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


def _parse_date(value: str) -> datetime.date:
    return datetime.date.fromisoformat(value)


_ROUTE_FIELD_CONVERTERS: dict[str, Callable[[Any], Any]] = {
    "company_id": lambda v: v,
    "start_point_id": lambda v: v,
    "end_point_id": lambda v: v,
    "dropp_off_point_id": lambda v: v,
    "effective_from": _parse_date,
    "effective_to": _parse_date,
    "comment": lambda v: v,
    "timetable": lambda v: v,
    "is_through": lambda v: v,
    "type": RouteType,
    "container_transfer_terms": ContainerTransferTerms,
    "container_shipment_terms": ContainerShipmentTerms,
    "container_owner": ContainerOwner,
}


def _build_route_kwargs(data: RouteSegmentCreate | RouteSegmentPatch) -> dict[str, Any]:
    kwargs = {}
    for field_name, converter in _ROUTE_FIELD_CONVERTERS.items():
        kwargs[field_name] = converter(getattr(data, field_name))
    return kwargs


_PATCH_CONVERTERS: dict[str, Callable[[Any], Any]] = {
    "effective_from": _parse_date,
    "effective_to": _parse_date,
    "type": RouteType,
    "container_transfer_terms": ContainerTransferTerms,
    "container_shipment_terms": ContainerShipmentTerms,
    "container_owner": ContainerOwner,
}


def _convert_patch_field(key: str, value: Any) -> Any:
    converter = _PATCH_CONVERTERS.get(key)
    return converter(value) if converter else value


class CRUDRouteSegment(CRUDBase):
    model = RouteModel
    create_schema = RouteSegmentCreate
    update_schema = RouteSegmentCreate
    patch_schema = RouteSegmentPatch
    response_schema = RouteSegmentResponse
    list_response_schema = RouteSegmentListResponse
    list_filters = [
        FilterDef("company_id", "company_id", "eq"),
        FilterDef("start_point_id", "start_point_id", "eq"),
        FilterDef("end_point_id", "end_point_id", "eq"),
    ]

    def _build_instance(self, data: RouteSegmentCreate) -> RouteModel:
        return RouteModel(**_build_route_kwargs(data))

    def _apply_update(self, model: RouteModel, data: RouteSegmentCreate) -> None:
        for key, value in _build_route_kwargs(data).items():
            setattr(model, key, value)

    def _apply_patch(self, model: RouteModel, data: RouteSegmentPatch) -> None:
        data_dump = data.model_dump(exclude_unset=True)
        for key, value in data_dump.items():
            if value is not None:
                setattr(model, key, _convert_patch_field(key, value))

    def _apply_list_filters(self, stmt: Any, **filters: Any) -> Any:
        stmt = super()._apply_list_filters(stmt, **filters)
        type_filter = filters.get("type")
        if type_filter is not None and type_filter != "":
            stmt = stmt.where(RouteModel.type == RouteType(type_filter))
        return stmt

    async def create(
        self, session: AsyncSession, data: RouteSegmentCreate
    ) -> RouteSegmentResponse:
        model = self._build_instance(data)
        session.add(model)
        await session.flush()

        for p in data.prices:
            session.add(PriceModel(route_id=model.id, **p.model_dump()))
        for s in data.services:
            session.add(ServicePriceModel(route_id=model.id, **s.model_dump()))

        await session.flush()
        return await self._reload_response(session, model.id)

    async def update(
        self, session: AsyncSession, id: int, data: RouteSegmentCreate  # noqa: A002
    ) -> RouteSegmentResponse:
        model = await self._load_with_relations(session, id)
        self._apply_update(model, data)

        for old_price in model.prices:
            await session.delete(old_price)
        for p in data.prices:
            session.add(PriceModel(route_id=model.id, **p.model_dump()))

        for old_service in model.services:
            await session.delete(old_service)
        for s in data.services:
            session.add(ServicePriceModel(route_id=model.id, **s.model_dump()))

        await session.flush()
        return await self._reload_response(session, id)

    async def patch(
        self, session: AsyncSession, id: int, data: RouteSegmentPatch  # noqa: A002
    ) -> RouteSegmentResponse:
        model = await self._load_with_relations(session, id)
        self._apply_patch(model, data)
        await session.flush()
        return await self._reload_response(session, id)

    async def get(self, session: AsyncSession, id: int) -> RouteSegmentResponse:  # noqa: A002
        model = await self._load_with_relations(session, id)
        return RouteSegmentResponse.from_model(model)

    async def list(  # noqa: A003
        self, session: AsyncSession, **filters: Any
    ) -> list[RouteSegmentListResponse]:
        stmt = select(RouteModel)
        stmt = self._apply_list_filters(stmt, **filters)
        result = await session.execute(stmt.order_by(RouteModel.id))
        return [RouteSegmentListResponse.from_model(m) for m in result.scalars()]

    async def _load_with_relations(self, session: AsyncSession, id: int) -> RouteModel:  # noqa: A002
        stmt = (
            select(RouteModel)
            .options(selectinload(RouteModel.prices), selectinload(RouteModel.services))
            .where(RouteModel.id == id)
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Route segment not found")
        return model

    async def _reload_response(self, session: AsyncSession, id: int) -> RouteSegmentResponse:  # noqa: A002
        return await self.get(session, id)


crud_route_segments = CRUDRouteSegment()
