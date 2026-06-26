from collections.abc import Iterable

import pandas as pd
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from module_data_internal.schemas import (
    CompanyModel,
    ContainerModel,
    ContainerOwner,
    ContainerShipmentTerms,
    ContainerTransferTerms,
    ContainerType,
    DropOffModel,
    PointModel,
    PriceModel,
    RouteSegmentModel,
    RouteSegmentType,
    ServiceModel,
    ServicePriceModel,
)
from pandas import DataFrame
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from .errors import (
    InvalidDropOffRow,
    InvalidRouteSegmentTypeException,
    NoPriceInRouteException,
    PointNotFoundException,
)
from .helpers import nan_to_none_mapper

ContainerRawType = dict[str, str | int | ContainerType]
ContainerUid = tuple[int, int, int]
ContainerStore = dict[ContainerUid, ContainerModel]

CompaniesStore = dict[str, CompanyModel]

ServicesStore = dict[str, ServiceModel]

PointsStore = list[PointModel]
PointsHashedStore = dict[str, PointModel]


async def load_companies(db_session, companies) -> CompaniesStore:
    models = {}
    existing_models = (await db_session.execute(select(CompanyModel))).scalars().all()

    for company in existing_models:
        models[company.name] = company

    for company in companies:
        if not models.get(company):
            models[company] = await db_session.merge(
                CompanyModel(name=company),
                load=True,
            )

    await db_session.commit()
    return models


async def load_points(db_session, df) -> PointsStore:
    models: list[PointModel | None] = [None] * len(df)
    existing_points = (await db_session.execute(select(PointModel))).scalars().all()
    existing_models_lower = {point.city.lower(): point for point in existing_points}

    for i, row in enumerate(df.itertuples()):
        arguments = row._asdict()
        del arguments["Index"]

        point = existing_models_lower.get(arguments["city"].lower())
        if not point:
            point = await db_session.merge(
                PointModel(**arguments),
                load=True,
            )
            existing_models_lower[point.city.lower()] = point

        models[i] = point

    await db_session.commit()
    return models  # type: ignore[return-value]


async def load_services(db_session, df: DataFrame, fc: UploaderFieldsConfig) -> ServicesStore:
    models = {}
    existing_models = (await db_session.execute(select(ServiceModel))).scalars().all()

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

            models[internal_name] = await db_session.merge(
                ServiceModel(
                    name=row[fc.service_name],
                    internal_name=internal_name,
                    description=nan_to_none_mapper(row[fc.description]) or "",
                    mandatory=mandatory,
                    default=default,
                ),
                load=True,
            )

    await db_session.commit()
    return models


async def load_containers(db_session, containers: list[ContainerRawType]) -> ContainerStore:
    models = {}
    existing_models = (await db_session.execute(select(ContainerModel))).scalars().all()

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
            models[container_complex_id] = await db_session.merge(
                ContainerModel(**container),
                load=True,
            )

    await db_session.commit()
    return models


def create_route_service(
    route: RouteSegmentModel,
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
    route: RouteSegmentModel,
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
    route_type: RouteSegmentType,
):
    # Container terms
    ctt = ContainerTransferTerms(row[fc.container_transfer_terms].upper())
    cst = ContainerShipmentTerms(row[fc.container_shipment_terms].upper())
    co = ContainerOwner(row[fc.container_condition].upper())

    sea_prices = None, None
    rail_prices = None, None, None

    if route_type is RouteSegmentType.SEA:
        sea_prices = tuple(map(nan_to_none_mapper, (
            row[fc.sea_20dc],
            row[fc.sea_40hc],
        )))

        if not any(sea_prices):
            raise NoPriceInRouteException

    elif route_type is RouteSegmentType.RAIL:
        rail_prices = tuple(map(nan_to_none_mapper, (
            row[fc.rail_20dc24t],
            row[fc.rail_20dc28t],
            row[fc.rail_40hc],
        )))

        if not any(rail_prices):
            raise NoPriceInRouteException

    else:
        raise InvalidRouteSegmentTypeException(route_type)

    company = companies[row[fc.company].upper()]

    try:
        start_point = points[row[fc.start_point].lower()]
        end_point = points[row[fc.end_point].lower()]
        dropp_off_point = (
            None if fc.dropp_off_point not in set(row.index.tolist()) or pd.isna(row[fc.dropp_off_point])
            else points[row[fc.dropp_off_point].lower()]
        )
    except KeyError as e:
        raise PointNotFoundException(e.args[0]) from e

    effective_from = row[fc.effective_from]
    effective_to = row[fc.effective_to]

    is_through_raw = row[fc.is_through]
    is_through = pd.isna(is_through_raw) or is_through_raw == 1.0 or is_through_raw == "1"

    route = RouteSegmentModel(
        type=RouteSegmentType(route_type),
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

    if route.type is RouteSegmentType.SEA:
        dc20_24t = sea_prices[0]
        dc20_24t_currency = "USD" if pd.isna(row[fc.sea_20dc_currency]) else row[fc.sea_20dc_currency].strip().upper()
        dc20_28t = dc20_24t
        dc20_28t_currency = dc20_24t_currency
        hc40 = sea_prices[1]
        hc40_currency = "USD" if pd.isna(row[fc.sea_40hc_currency]) else row[fc.sea_40hc_currency].strip().upper()
    elif route.type is RouteSegmentType.RAIL:
        dc20_24t = rail_prices[0]
        dc20_24t_currency = (
            "РУБ" if pd.isna(row[fc.rail_20dc24t_currency]) else row[fc.rail_20dc24t_currency].strip().upper()
        )
        dc20_28t = rail_prices[1]
        dc20_28t_currency = (
            "РУБ" if pd.isna(row[fc.rail_20dc28t_currency]) else row[fc.rail_20dc28t_currency].strip().upper()
        )
        hc40 = rail_prices[2]
        hc40_currency = "РУБ" if pd.isna(row[fc.rail_40hc_currency]) else row[fc.rail_40hc_currency].strip().upper()
    else:
        raise InvalidRouteSegmentTypeException(route_type)

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


def create_drop_off(
    containers: ContainerStore,
    companies: CompaniesStore,
    points: PointsHashedStore,
    row,
    fc: UploaderFieldsConfig,
):
    company = companies.get(row[fc.company].upper())
    start_point = points.get(row[fc.start_point].lower())
    end_point = points.get(row[fc.end_point].lower())
    effective_from = row[fc.effective_from]
    effective_to = row[fc.effective_to]

    currency = "USD"
    price_20dc = row[fc.drop20]
    price_40hc = row[fc.drop40]
    conversation_percents = row[fc.conversation_percents]

    if not all((company, start_point, end_point, effective_from, effective_to)):
        raise InvalidDropOffRow

    base_config = {
        "start_point": start_point,
        "end_point": end_point,
        "company": company,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "conversation_percents": conversation_percents,
        "currency": currency,
    }

    all_drop_off: list[DropOffModel] = []
    if price_20dc is not None and not pd.isna(price_20dc):
        all_drop_off.extend((
            DropOffModel(**base_config, price=price_20dc, container=containers[(20, 0, 24)]),
            DropOffModel(**base_config, price=price_20dc, container=containers[(20, 24, 28)]),
        ))
    if price_40hc is not None and not pd.isna(price_40hc):
        all_drop_off.append(DropOffModel(**base_config, price=price_40hc, container=containers[(40, 0, 28)]))

    return all_drop_off


async def load_routes(db_session, routes):
    existing_routes = (await db_session.execute(select(RouteSegmentModel).options(
        joinedload(RouteSegmentModel.start_point),
        joinedload(RouteSegmentModel.end_point),
        joinedload(RouteSegmentModel.company),
    ))).scalars().all()

    existing_routes_set = {(  # noqa: ECE001
        route.company.name,
        route.start_point.city,
        route.end_point.city,
        route.dropp_off_point.city if route.dropp_off_point else None,
        route.effective_from if isinstance(route.effective_from, str) else route.effective_from.date().isoformat(),
        route.effective_to if isinstance(route.effective_to, str) else route.effective_to.date().isoformat(),
        route.container_shipment_terms,
        route.container_transfer_terms,
        route.container_owner,
        route.is_through,
    ) for route in existing_routes}

    for route in routes:
        route_key = (
            route.company.name,
            route.start_point.city,
            route.end_point.city,
            route.dropp_off_point.city if route.dropp_off_point else None,
            route.effective_from if isinstance(route.effective_from, str) else route.effective_from.date().isoformat(),
            route.effective_to if isinstance(route.effective_to, str) else route.effective_to.date().isoformat(),
            route.container_shipment_terms,
            route.container_transfer_terms,
            route.container_owner,
            route.is_through,
        )
        if route_key in existing_routes_set:
            continue

        await db_session.merge(route)
        existing_routes_set.add(route_key)

    await db_session.commit()


async def load_drop_off(db_session, drop_off_groups: list[Iterable[DropOffModel]]):
    existing_drop_off = (await db_session.execute(select(DropOffModel).options(
        joinedload(DropOffModel.start_point),
        joinedload(DropOffModel.end_point),
        joinedload(DropOffModel.company),
        joinedload(DropOffModel.container),
    ))).scalars().all()

    existing_drop_off_set = {(  # noqa: ECE001
        item.start_point.city,
        item.end_point.city,
        item.company.name,
        (item.container.size, item.container.weight_from, item.container.weight_to),
        item.effective_from if isinstance(item.effective_from, str) else item.effective_from.date().isoformat(),
        item.effective_to if isinstance(item.effective_to, str) else item.effective_to.date().isoformat(),
    ) for item in existing_drop_off}

    for items_group in drop_off_groups:
        for item in items_group:
            drop_off_key = (
                item.start_point.city,
                item.end_point.city,
                item.company.name,
                (item.container.size, item.container.weight_from, item.container.weight_to),
                item.effective_from if isinstance(item.effective_from, str) else item.effective_from.date().isoformat(),
                item.effective_to if isinstance(item.effective_to, str) else item.effective_to.date().isoformat(),
            )
            if drop_off_key in existing_drop_off_set:
                continue

            await db_session.merge(item)
            existing_drop_off_set.add(drop_off_key)

    await db_session.commit()
