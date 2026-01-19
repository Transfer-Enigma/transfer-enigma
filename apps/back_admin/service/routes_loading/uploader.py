from shared.models import (
    CompanyModel,
    ContainerModel,
    ContainerType,
    DropModel,
    PointModel,
    PriceModel,
    PriceTypeEnum,
    RouteModel,
    RouteTypeEnum,
)
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from .errors import (
    InvalidRouteConditionCurrencyPairException,
    InvalidRouteConditionException,
    InvalidRouteConditionPricesException,
    InvalidRouteTypeException,
    PointNotFoundException,
)
from .helpers import nan_to_none_mapper


async def load_services(db_session, services):
    models = {}
    existing_models = (await db_session.execute(select(CompanyModel))).scalars().all()

    for service in existing_models:
        models[service.name] = service

    for service in services:
        if not models.get(service):
            models[service] = await db_session.merge(
                CompanyModel(name=service),
                load=True,
            )

    await db_session.commit()
    return models


async def load_points(db_session, df):
    models = [None] * len(df)
    existing_models = {point.city: point for point in (await db_session.execute(select(PointModel))).scalars().all()}

    for i, row in enumerate(df.itertuples()):
        arguments = row._asdict()
        del arguments["Index"]

        point = existing_models.get(arguments["city"])
        if not point:
            point = await db_session.merge(
                PointModel(**arguments),
                load=True,
            )
            existing_models[point.city] = point

        models[i] = point

    await db_session.commit()
    return models


async def load_containers(db_session, containers):
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


def create_route(containers, services, points, row, fc):
    cond = tuple([x.strip() for x in row[fc["condition"]].upper().split("/")])

    sea_prices = tuple(map(nan_to_none_mapper, (
        row[fc["sea_20dc"]],
        row[fc["sea_40hc"]],
    )))
    rail_prices = tuple(map(nan_to_none_mapper, (
        row[fc["rail_20dc24t"]],
        row[fc["rail_20dc28t"]],
        row[fc["rail_40hc"]],
    )))
    drop_prices = tuple(map(nan_to_none_mapper, (
        row[fc["drop20"]],
        row[fc["drop40"]],
    )))

    if (len(cond) == 1 and (
        (cond[0] == PriceTypeEnum.FIFOR.value or cond[0] == PriceTypeEnum.FILO.value) and not any(sea_prices)
        or cond[0] == PriceTypeEnum.FOBFOR.value and not any(rail_prices)
    )) or len(cond) > 1 and not any(sea_prices) and not any(rail_prices):
        raise InvalidRouteConditionPricesException(cond, sea_prices, rail_prices)

    service = services[row[fc["service"]]]

    try:
        start_point = points[row[fc["start_point"]]]
        end_point = points[row[fc["end_point"]]]
    except KeyError as e:
        raise PointNotFoundException(e.args[0]) from e

    effective_from = row[fc["effective_from"]]
    effective_to = row[fc["effective_to"]]

    route_types_map = {
        "море": "sea",
        "жд": "rail",
        "море+жд": "sea_rail",
    }

    try:
        route_type = RouteTypeEnum(route_types_map[row[fc["type"]]])
    except KeyError:
        raise InvalidRouteTypeException(row[fc["type"]])

    route = RouteModel(
        type=route_type,
        company=service,
        start_point=start_point,
        end_point=end_point,
        effective_from=effective_from,
        effective_to=effective_to,
        comment=nan_to_none_mapper(row[fc["comment"]]),
    )

    try:
        types = [PriceTypeEnum(x.strip()) for x in row[fc["condition"]].split("/")]
    except ValueError as e:
        raise InvalidRouteConditionException(row[fc["condition"]]) from e

    currencies = [x.strip() for x in row[fc["currency"]].split("/")]
    conversation = nan_to_none_mapper(row[fc["conversation_percents"]])

    if (len(types) > 2 or len(types) < 1 or len(types) != len(currencies)
        or len(types) == len(currencies) == 2 and route.type is not RouteTypeEnum.SEA_RAIL
        or len(types) == len(currencies) == 1 and route.type not in (RouteTypeEnum.SEA, RouteTypeEnum.RAIL)):
        raise InvalidRouteConditionCurrencyPairException([t.value for t in types], currencies, route.type)

    base_drop_config = {
        "company": service,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "currency": "USD",
        "conversation_percents": conversation,
    }
    base_sea_drop_config = {
        **base_drop_config,
        "sea_start_point": start_point,
        "sea_end_point": end_point,
    }
    base_rail_drop_config = {
        **base_drop_config,
        "rail_start_point": start_point,
        "rail_end_point": end_point,
    }
    base_mixed_drop_config = {
        **base_drop_config,
        "sea_start_point": start_point,
        "rail_end_point": end_point,
    }

    if route.type is RouteTypeEnum.SEA:
        dc20_24t = (sea_prices[0],)
        dc20_28t = dc20_24t
        hc40 = (sea_prices[1],)

        drop20 = drop_prices[0]
        drop40 = drop_prices[1]

        drop = [] if drop20 is None else [
            DropModel(**base_sea_drop_config, price=drop20, container=containers[(20, 0, 24)]),
            DropModel(**base_sea_drop_config, price=drop20, container=containers[(20, 24, 28)]),
        ]

        if drop40 is not None:
            drop.append(DropModel(**base_sea_drop_config, price=drop40, container=containers[(40, 0, 28)]))

    elif route.type is RouteTypeEnum.RAIL:
        dc20_24t = (rail_prices[0],)
        dc20_28t = (rail_prices[1],)
        hc40 = (rail_prices[2],)

        drop20 = drop_prices[0]
        drop40 = drop_prices[1]

        drop = [] if drop20 is None else [
            DropModel(**base_rail_drop_config, price=drop20, container=containers[(20, 0, 24)]),
            DropModel(**base_rail_drop_config, price=drop20, container=containers[(20, 24, 28)]),
        ]

        if drop40 is not None:
            drop.append(DropModel(**base_rail_drop_config, price=drop40, container=containers[(40, 0, 28)]))

    elif route.type is RouteTypeEnum.SEA_RAIL:
        dc20_24t = (sea_prices[0], rail_prices[0])
        dc20_28t = (sea_prices[0], rail_prices[1])
        hc40 = (sea_prices[1], rail_prices[2])

        drop20 = drop_prices[0]
        drop40 = drop_prices[1]

        drop = [] if drop20 is None else [
            DropModel(**base_mixed_drop_config, price=drop20, container=containers[(20, 0, 24)]),
            DropModel(**base_mixed_drop_config, price=drop20, container=containers[(20, 24, 28)]),
        ]

        if drop40 is not None:
            drop.append(DropModel(**base_mixed_drop_config, price=drop40, container=containers[(40, 0, 28)]))
    else:
        raise InvalidRouteTypeException(route.type)

    if dc20_24t:
        PriceModel(
            container=containers[(20, 0, 24)],
            route=route,
            currency=currencies[0],
            value=dc20_24t[0],
            type=types[0],
            conversation_percents=conversation,
        )

        if route.type is RouteTypeEnum.SEA_RAIL:
            PriceModel(
                container=containers[(20, 0, 24)],
                route=route,
                currency=currencies[1],
                value=dc20_24t[1],
                type=types[1],
                conversation_percents=conversation,
            )
    if dc20_28t:
        PriceModel(
            container=containers[(20, 24, 28)],
            route=route,
            currency=currencies[0],
            value=dc20_28t[0],
            type=types[0],
            conversation_percents=conversation,
        )

        if route.type is RouteTypeEnum.SEA_RAIL:
            PriceModel(
                container=containers[(20, 24, 28)],
                route=route,
                currency=currencies[1],
                value=dc20_28t[1],
                type=types[1],
                conversation_percents=conversation,
            )
    if hc40:
        PriceModel(
            container=containers[(40, 0, 28)],
            route=route,
            currency=currencies[0],
            value=hc40[0],
            type=types[0],
            conversation_percents=conversation,
        )

        if route.type is RouteTypeEnum.SEA_RAIL:
            PriceModel(
                container=containers[(40, 0, 28)],
                route=route,
                currency=currencies[1],
                value=hc40[1],
                type=types[1],
                conversation_percents=conversation,
            )

    return route, drop


async def load_routes(db_session, routes_and_drop):
    existing_routes = (await db_session.execute(select(RouteModel).options(
        joinedload(RouteModel.start_point),
        joinedload(RouteModel.end_point),
        joinedload(RouteModel.company),
    ))).scalars().all()

    existing_drops = (await db_session.execute(select(DropModel).options(
        joinedload(DropModel.sea_start_point),
        joinedload(DropModel.sea_end_point),
        joinedload(DropModel.rail_start_point),
        joinedload(DropModel.rail_end_point),
        joinedload(DropModel.company),
        joinedload(DropModel.container),
    ))).scalars().all()

    existing_routes_set = {(
        route.company.name,
        route.start_point.city,
        route.end_point.city,
        route.effective_from if isinstance(route.effective_from, str) else route.effective_from.date().isoformat(),
        route.effective_to if isinstance(route.effective_to, str) else route.effective_to.date().isoformat(),
    ) for route in existing_routes}

    existing_drops_set = {(
        drop.sea_start_point.city if drop.sea_start_point else None,
        drop.sea_end_point.city if drop.sea_end_point else None,
        drop.rail_start_point.city if drop.rail_start_point else None,
        drop.rail_end_point.city if drop.rail_end_point else None,
        drop.container.name,
        drop.company.name,
    ) for drop in existing_drops}

    for route, drop_list in routes_and_drop:
        for drop in drop_list:
            drop_key = (
                drop.sea_start_point.city if drop.sea_start_point else None,
                drop.sea_end_point.city if drop.sea_end_point else None,
                drop.rail_start_point.city if drop.rail_start_point else None,
                drop.rail_end_point.city if drop.rail_end_point else None,
                drop.container.name,
                drop.company.name,
            )

            if drop_key in existing_drops_set:
                continue

            await db_session.merge(drop)
            existing_drops_set.add(drop_key)

        route_key = (
            route.company.name,
            route.start_point.city,
            route.end_point.city,
            route.effective_from if isinstance(route.effective_from, str) else route.effective_from.date().isoformat(),
            route.effective_to if isinstance(route.effective_to, str) else route.effective_to.date().isoformat(),
        )
        if route_key in existing_routes_set:
            continue

        await db_session.merge(route)
        existing_routes_set.add(route_key)

    await db_session.commit()
