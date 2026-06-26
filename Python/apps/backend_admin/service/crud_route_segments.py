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
    RouteSegmentStatsResponse,
)
from backend_admin.service.crud_base import CRUDBase, FilterDef
from module_data_internal.schemas.company import CompanyModel
from module_data_internal.schemas.route import (
    ContainerOwner,
    ContainerShipmentTerms,
    ContainerTransferTerms,
    PriceModel,
    RouteSegmentModel,
    RouteType,
    ServicePriceModel,
)
from sqlalchemy import func, select
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
    model = RouteSegmentModel
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

    def _build_instance(self, data: RouteSegmentCreate) -> RouteSegmentModel:
        return RouteSegmentModel(**_build_route_kwargs(data))

    def _apply_update(self, model: RouteSegmentModel, data: RouteSegmentCreate) -> None:
        for key, value in _build_route_kwargs(data).items():
            setattr(model, key, value)

    def _apply_patch(self, model: RouteSegmentModel, data: RouteSegmentPatch) -> None:
        data_dump = data.model_dump(exclude_unset=True)
        for key, value in data_dump.items():
            if value is not None:
                setattr(model, key, _convert_patch_field(key, value))

    def _apply_list_filters(self, stmt: Any, **filters: Any) -> Any:
        stmt = super()._apply_list_filters(stmt, **filters)
        type_filter = filters.get("type")
        if type_filter is not None and type_filter != "":
            stmt = stmt.where(RouteSegmentModel.type == RouteType(type_filter.upper()))
        return stmt

    async def stats(
        self, session: AsyncSession
    ) -> RouteSegmentStatsResponse:
        # Total
        total_result = await session.execute(select(func.count(RouteSegmentModel.id)))
        total = total_result.scalar() or 0

        # By type
        type_result = await session.execute(
            select(RouteSegmentModel.type, func.count(RouteSegmentModel.id))
            .group_by(RouteSegmentModel.type)
        )
        by_type: dict[str, int] = {str(r[0].value): r[1] for r in type_result}

        # By is_through
        through_result = await session.execute(
            select(RouteSegmentModel.is_through, func.count(RouteSegmentModel.id))
            .group_by(RouteSegmentModel.is_through)
        )
        by_is_through: dict[str, int] = {str(r[0]).lower(): r[1] for r in through_result}

        # By container_owner
        owner_result = await session.execute(
            select(RouteSegmentModel.container_owner, func.count(RouteSegmentModel.id))
            .group_by(RouteSegmentModel.container_owner)
        )
        by_container_owner: dict[str, int] = {str(r[0].value): r[1] for r in owner_result}

        # Top companies (limit 20)
        cnt_col = func.count(RouteSegmentModel.id).label("cnt")
        sq = select(RouteSegmentModel.company_id, CompanyModel.name, cnt_col)
        sq = sq.join(CompanyModel, RouteSegmentModel.company_id == CompanyModel.id)
        sq = sq.group_by(RouteSegmentModel.company_id, CompanyModel.name)
        sq = sq.order_by(cnt_col.desc())
        sq = sq.limit(20)
        companies_result = await session.execute(sq)
        top_companies = [
            {"company_id": r[0], "name": r[1], "count": r[2]}
            for r in companies_result
        ]

        return RouteSegmentStatsResponse(
            total_segments=total,
            by_type=by_type,
            by_is_through=by_is_through,
            by_container_owner=by_container_owner,
            top_companies=top_companies,
        )

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
        stmt = select(RouteSegmentModel)
        stmt = self._apply_list_filters(stmt, **filters)
        result = await session.execute(stmt.order_by(RouteSegmentModel.id))
        return [RouteSegmentListResponse.from_model(m) for m in result.scalars()]

    async def _load_with_relations(self, session: AsyncSession, id: int) -> RouteSegmentModel:  # noqa: A002
        stmt = (
            select(RouteSegmentModel)
            .options(selectinload(RouteSegmentModel.prices), selectinload(RouteSegmentModel.services))
            .where(RouteSegmentModel.id == id)
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Route segment not found")
        return model

    async def _reload_response(self, session: AsyncSession, id: int) -> RouteSegmentResponse:  # noqa: A002
        return await self.get(session, id)


crud_route_segments = CRUDRouteSegment()
