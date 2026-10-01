from collections.abc import Iterable

import pandas as pd
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from module_shared.schemas.company import CompanyModel
from module_shared.schemas.container import ContainerModel, ContainerType
from module_shared.schemas.drop import DropModel
from module_shared.schemas.point import PointModel
from module_shared.schemas.route import (
    ContainerOwner,
    ContainerShipmentTerms,
    ContainerTransferTerms,
    PriceModel,
    RouteModel,
    RouteType,
    ServicePriceModel,
)
from module_shared.schemas.service import ServiceModel
from pandas import DataFrame
from sqlalchemy import delete, select
from sqlalchemy.orm import joinedload

from .errors import (
    CompanyNotFoundException,
    InvalidDroppRow,
    InvalidRouteTypeException,
    NoPriceInRouteException,
    PointNotFoundException,
)
from .helpers import nan_to_none_mapper, to_date
from .uid import (
    fingerprint_drop,
    fingerprint_route,
    natural_uid_for_dropp_item,
    natural_uid_for_route_model,
)
from .unit_of_work import UnitOfWork

ContainerRawType = dict[str, str | int | ContainerType]
ContainerUid = tuple[int, int, int]
ContainerStore = dict[ContainerUid, ContainerModel]

CompaniesStore = dict[str, CompanyModel]

ServicesStore = dict[str, ServiceModel]

PointsStore = list[PointModel]
PointsHashedStore = dict[str, PointModel]


async def load_companies(uow: UnitOfWork, companies) -> CompaniesStore:
    models = {}
    existing_models = (await uow.session.execute(select(CompanyModel))).scalars().all()

    for company in existing_models:
        models[company.name] = company

    for company in companies:
        if not models.get(company):
            models[company] = await uow.session.merge(
                CompanyModel(name=company),
                load=True,
            )

    await uow.commit()
    return models


async def load_points(uow: UnitOfWork, df) -> PointsStore:
    models: list[PointModel | None] = [None] * len(df)
    existing_points = (await uow.session.execute(select(PointModel))).scalars().all()
    existing_models_lower = {point.city.lower(): point for point in existing_points}

    for i, row in enumerate(df.itertuples()):
        arguments = row._asdict()
        del arguments["Index"]

        point = existing_models_lower.get(arguments["city"].lower())
        if not point:
            point = await uow.session.merge(
                PointModel(**arguments),
                load=True,
            )
            existing_models_lower[point.city.lower()] = point

        models[i] = point

    await uow.commit()
    return models  # type: ignore[return-value]


async def load_services(uow: UnitOfWork, df: DataFrame, fc: UploaderFieldsConfig) -> ServicesStore:
    models = {}
    existing_models = (await uow.session.execute(select(ServiceModel))).scalars().all()

    for service in existing_models:
        models[service.internal_name] = service

    for _, row in df.iterrows():
        internal_name = row[fc.column_name]

        if not models.get(internal_name):
            including = row[fc.including]
            if not including or pd.isna(including):
                mandatory = default = False
            elif including == 1:
                default = True
                mandatory = False
            else:
                mandatory = default = True

            models[internal_name] = await uow.session.merge(
                ServiceModel(
                    name=row[fc.service_name],
                    internal_name=internal_name,
                    description=nan_to_none_mapper(row[fc.description]) or "",
                    mandatory=mandatory,
                    default=default,
                ),
                load=True,
            )

    await uow.commit()
    return models


async def load_containers(uow: UnitOfWork, containers: list[ContainerRawType]) -> ContainerStore:
    models = {}
    existing_models = (await uow.session.execute(select(ContainerModel))).scalars().all()

    for container in existing_models:
        models[(
            container.size,
            container.weight_from,
            container.weight_to,
        )] = container

    for container in containers:
        container_complex_id = (
            container["size"],
            container["weight_from"],
            container["weight_to"],
        )
        if not models.get(container_complex_id):
            container["type"] = ContainerType(container["type"])
            models[container_complex_id] = await uow.session.merge(
                ContainerModel(**container),
                load=True,
            )

    await uow.commit()
    return models


def create_route_service(
    route: RouteModel,
    services: ServicesStore,
    container: ContainerModel | None,
    service_column_name: str,
    row,
    fc: UploaderFieldsConfig,
):
    price_column = getattr(fc, service_column_name)
    currency_column = getattr(fc, f"{service_column_name}_currency")

    internal_service_name = price_column.split("#")[0].strip()
    service = services.get(internal_service_name)
    if not service:
        return

    currency = row[currency_column]
    price = nan_to_none_mapper(row[price_column])
    if not price:
        return

    return ServicePriceModel(
        route=route,
        service=service,
        container=container,
        currency=nan_to_none_mapper(currency) or "USD",
        price=float(price),
    )


def create_route_services(
    route: RouteModel,
    services: ServicesStore,
    containers: ContainerStore,
    row,
    fc: UploaderFieldsConfig,
):
    for service_column_name in fc.services:
        create_route_service(route, services, None, service_column_name, row, fc)

    for service_column_name, container_descriptor in fc.services_with_container.items():
        container = containers.get(container_descriptor)
        if container:
            create_route_service(route, services, container, service_column_name, row, fc)


def create_route(  # noqa: C901
    containers: ContainerStore,
    companies: CompaniesStore,
    points: PointsHashedStore,
    services: ServicesStore,
    row,
    fc: UploaderFieldsConfig,
    route_type: RouteType,
):
    # Container terms
    ctt = ContainerTransferTerms(row[fc.container_transfer_terms].upper())
    cst = ContainerShipmentTerms(row[fc.container_shipment_terms].upper())
    co = ContainerOwner(row[fc.container_condition].upper())

    sea_prices = None, None
    rail_prices = None, None, None
    truck_prices = None, None

    if route_type is RouteType.SEA:
        sea_prices = tuple(map(nan_to_none_mapper, (
            row[fc.sea_20dc],
            row[fc.sea_40hc],
        )))

        if not any(sea_prices):
            raise NoPriceInRouteException

    elif route_type is RouteType.RAIL:
        rail_prices = tuple(map(nan_to_none_mapper, (
            row[fc.rail_20dc24t],
            row[fc.rail_20dc28t],
            row[fc.rail_40hc],
        )))

        if not any(rail_prices):
            raise NoPriceInRouteException

    elif route_type is RouteType.TRUCK:
        truck_prices = tuple(map(nan_to_none_mapper, (
            row[fc.truck_20dc],
            row[fc.truck_40hc],
        )))

        if not any(truck_prices):
            raise NoPriceInRouteException

    else:
        raise InvalidRouteTypeException(route_type)

    company_name = row[fc.company]
    if company_name not in companies:
        raise PointNotFoundException(row[fc.company])
    company = companies[company_name]

    try:
        start_point = points[row[fc.start_point].lower()]
        end_point = points[row[fc.end_point].lower()]
        dropp_off_point = (
            None if pd.isna(row[fc.dropp_off_point])
            else points.get(row[fc.dropp_off_point].lower())
        )
    except KeyError as e:
        raise PointNotFoundException(e.args[0]) from e

    effective_from = to_date(row[fc.effective_from])
    effective_to = to_date(row[fc.effective_to])

    is_through = bool(row[fc.is_through])

    route = RouteModel(
        type=RouteType(route_type),
        company=company,
        start_point=start_point,
        end_point=end_point,
        dropp_off_point=dropp_off_point,
        effective_from=effective_from,
        effective_to=effective_to,
        comment=nan_to_none_mapper(row[fc.comment]),
        timetable=nan_to_none_mapper(row[fc.timetable]),
        container_transfer_terms=ctt,
        container_shipment_terms=cst,
        container_owner=co,
        is_through=is_through,
    )

    conversation = nan_to_none_mapper(row[fc.conversation_percents])

    if route.type is RouteType.SEA:
        dc20_24t = sea_prices[0]
        dc20_24t_currency = row[fc.sea_20dc_currency].strip().upper() if pd.notna(row[fc.sea_20dc_currency]) else "USD"
        dc20_28t = dc20_24t
        dc20_28t_currency = dc20_24t_currency
        hc40 = sea_prices[1]
        hc40_currency = row[fc.sea_40hc_currency].strip().upper() if pd.notna(row[fc.sea_40hc_currency]) else "USD"
    elif route.type is RouteType.RAIL:
        dc20_24t = rail_prices[0]
        dc20_24t_currency = row[fc.rail_20dc24t_currency].strip().upper() or "РУБ"
        dc20_28t = rail_prices[1]
        dc20_28t_currency = row[fc.rail_20dc28t_currency].strip().upper() or "РУБ"
        hc40 = rail_prices[2]
        hc40_currency = row[fc.rail_40hc_currency].strip().upper() or "РУБ"
    elif route.type is RouteType.TRUCK:
        dc20_24t = truck_prices[0]
        dc20_24t_currency = row[fc.truck_20dc_currency].strip().upper()
        dc20_28t = None
        dc20_28t_currency = "РУБ"
        hc40 = truck_prices[1]
        hc40_currency = row[fc.truck_40hc_currency].strip().upper()
    else:
        raise InvalidRouteTypeException(route_type)

    if dc20_24t is not None:
        PriceModel(
            container=containers[(20, 0, 24)],
            route=route,
            currency=dc20_24t_currency,
            value=dc20_24t,
            conversation_percents=conversation,
        )
    if dc20_28t is not None:
        PriceModel(
            container=containers[(20, 24, 28)],
            route=route,
            currency=dc20_28t_currency,
            value=dc20_28t,
            conversation_percents=conversation,
        )
    if hc40 is not None:
        PriceModel(
            container=containers[(40, 0, 28)],
            route=route,
            currency=hc40_currency,
            value=hc40,
            conversation_percents=conversation,
        )

    create_route_services(route, services, containers, row, fc)

    return route


def create_dropp(
    containers: ContainerStore,
    companies: CompaniesStore,
    points: PointsHashedStore,
    row,
    fc: UploaderFieldsConfig,
):
    company_name = row[fc.company]
    if not company_name:
        raise InvalidDroppRow

    company_name = company_name.upper()
    if company_name not in companies:
        raise CompanyNotFoundException(row[fc.company])

    company = companies[company_name]

    try:
        start_point = points[(row[fc.start_point] or "").lower()]
        end_point = points[(row[fc.end_point] or "").lower()]
    except KeyError as e:
        raise PointNotFoundException(e.args[0]) from e

    effective_from = to_date(row[fc.effective_from])
    effective_to = to_date(row[fc.effective_to])

    if not effective_from or not effective_to:
        raise InvalidDroppRow

    currency = "USD"
    price_20dc = row[fc.drop20]
    price_40hc = row[fc.drop40]
    conversation_percents = row[fc.conversation_percents]

    base_config = {
        "start_point": start_point,
        "end_point": end_point,
        "company": company,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "conversation_percents": conversation_percents,
        "currency": currency,
    }

    all_dropp: list[DropModel] = []
    if price_20dc is not None and not pd.isna(price_20dc):
        all_dropp.extend((
            DropModel(**base_config, price=price_20dc, container=containers[(20, 0, 24)]),
            DropModel(**base_config, price=price_20dc, container=containers[(20, 24, 28)]),
        ))
    if price_40hc is not None and not pd.isna(price_40hc):
        all_dropp.append(DropModel(**base_config, price=price_40hc, container=containers[(40, 0, 28)]))

    return all_dropp


def _scope_of(route: RouteModel) -> str:
    route_type = route.type
    return route_type.value if hasattr(route_type, "value") else str(route_type)


def _container_key_of(container) -> tuple:
    return (container.size, container.weight_from, container.weight_to)


async def _update_route(uow: UnitOfWork, persistent_id: int, route: RouteModel) -> None:
    persistent = await uow.session.get(RouteModel, persistent_id)
    if persistent is None:
        await uow.session.merge(route)
        return
    persistent.type = route.type
    persistent.company = route.company
    persistent.start_point = route.start_point
    persistent.end_point = route.end_point
    persistent.dropp_off_point = route.dropp_off_point
    persistent.effective_from = route.effective_from
    persistent.effective_to = route.effective_to
    persistent.comment = route.comment
    persistent.timetable = route.timetable
    persistent.container_transfer_terms = route.container_transfer_terms
    persistent.container_shipment_terms = route.container_shipment_terms
    persistent.container_owner = route.container_owner
    persistent.is_through = route.is_through
    persistent.payload_hash = route.payload_hash
    if route.sync_document_id is not None:
        persistent.sync_document_id = route.sync_document_id

    await uow.session.execute(delete(PriceModel).where(PriceModel.route_id == persistent_id))
    await uow.session.execute(
        delete(ServicePriceModel).where(ServicePriceModel.route_id == persistent_id),
    )
    for price in list(route.prices):
        price.route = persistent
        uow.session.add(price)
    for service_price in list(route.services):
        service_price.route = persistent
        uow.session.add(service_price)


async def load_routes(uow: UnitOfWork, routes, update_existing: bool = True,
                      sync_document_id: int | None = None,
                      present_by_scope: dict[str, frozenset[str]] | None = None) -> int:
    existing_routes = (await uow.session.execute(select(RouteModel).options(
        joinedload(RouteModel.start_point),
        joinedload(RouteModel.end_point),
        joinedload(RouteModel.dropp_off_point),
        joinedload(RouteModel.company),
    ))).scalars().all()

    existing_map = {natural_uid_for_route_model(route): route for route in existing_routes}

    for route in routes:
        uid = natural_uid_for_route_model(route)
        route.payload_hash = fingerprint_route(route)
        if sync_document_id is not None:
            route.sync_document_id = sync_document_id

        existing = existing_map.get(uid)
        if existing is None:
            await uow.session.merge(route)
            existing_map[uid] = route
            continue
        if update_existing and sync_document_id is not None and existing.sync_document_id != sync_document_id:
            existing.sync_document_id = sync_document_id
        if existing.payload_hash != route.payload_hash and update_existing:
            await _update_route(uow, existing.id, route)
            existing_map[uid] = route

    deleted = 0
    if update_existing and present_by_scope is not None:
        missing_ids = [
            route.id for route in existing_routes
            if _scope_of(route) in present_by_scope
            and natural_uid_for_route_model(route) not in present_by_scope[_scope_of(route)]
        ]
        if missing_ids:
            await uow.session.execute(
                delete(ServicePriceModel).where(ServicePriceModel.route_id.in_(missing_ids)),
            )
            await uow.session.execute(
                delete(PriceModel).where(PriceModel.route_id.in_(missing_ids)),
            )
            await uow.session.execute(delete(RouteModel).where(RouteModel.id.in_(missing_ids)))
            deleted = len(missing_ids)

    await uow.commit()
    return deleted


async def _update_drop(uow: UnitOfWork, persistent_id: int, item: DropModel) -> None:
    persistent = await uow.session.get(DropModel, persistent_id)
    if persistent is None:
        await uow.session.merge(item)
        return
    persistent.start_point = item.start_point
    persistent.end_point = item.end_point
    persistent.company = item.company
    persistent.container = item.container
    persistent.effective_from = item.effective_from
    persistent.effective_to = item.effective_to
    persistent.price = item.price
    persistent.conversation_percents = item.conversation_percents
    persistent.currency = item.currency
    persistent.payload_hash = item.payload_hash
    if item.sync_document_id is not None:
        persistent.sync_document_id = item.sync_document_id


async def load_dropp(uow: UnitOfWork, dropp: list[Iterable[DropModel]], update_existing: bool = True,
                     sync_document_id: int | None = None,
                     present_by_scope: dict[str, frozenset[str]] | None = None) -> int:
    existing_dropp = (await uow.session.execute(select(DropModel).options(
        joinedload(DropModel.start_point),
        joinedload(DropModel.end_point),
        joinedload(DropModel.company),
        joinedload(DropModel.container),
    ))).scalars().all()

    existing_dropp_map = {
        (natural_uid_for_dropp_item(item), _container_key_of(item.container)): item
        for item in existing_dropp
    }

    for items_group in dropp:
        for item in items_group:
            uid = natural_uid_for_dropp_item(item)
            item.payload_hash = fingerprint_drop(item)
            if sync_document_id is not None:
                item.sync_document_id = sync_document_id

            match_key = (uid, _container_key_of(item.container))
            existing = existing_dropp_map.get(match_key)
            if existing is None:
                await uow.session.merge(item)
                existing_dropp_map[match_key] = item
                continue
            if update_existing and sync_document_id is not None and existing.sync_document_id != sync_document_id:
                existing.sync_document_id = sync_document_id
            if existing.payload_hash != item.payload_hash and update_existing:
                await _update_drop(uow, existing.id, item)
                existing_dropp_map[match_key] = item

    deleted = 0
    if update_existing and present_by_scope is not None and "DROPP" in present_by_scope:
        present = present_by_scope["DROPP"]
        missing_ids = [
            item.id for item in existing_dropp
            if natural_uid_for_dropp_item(item) not in present
        ]
        if missing_ids:
            await uow.session.execute(delete(DropModel).where(DropModel.id.in_(missing_ids)))
            deleted = len(missing_ids)

    await uow.commit()
    return deleted
