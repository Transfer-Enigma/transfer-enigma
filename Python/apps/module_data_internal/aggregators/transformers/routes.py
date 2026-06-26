from module_data_internal.schemas import DropOffModel, PriceModel, RouteModel
from module_shared.database import Base
from module_shared.models.route import (
    ContainerItem,
    DropOffItem,
    PriceItem,
    Route,
    RouteSegment,
    ServiceItem,
)


def _transform_container_from_orm(price: PriceModel) -> ContainerItem:
    c = price.container
    return ContainerItem(
        id=c.id,
        type=c.type.value,
        size=c.size,
        weight_from=c.weight_from,
        weight_to=c.weight_to,
        name=c.name,
    )


def _segment_from_orm(route: RouteModel) -> RouteSegment:
    prices: list[PriceItem] = [
        PriceItem(
            container=_transform_container_from_orm(p),
            value=p.value,
            currency=p.currency,
            conversation_percents=p.conversation_percents,
        )
        for p in route.prices
    ]

    return RouteSegment(
        id=route.id,
        company=route.company.name,
        type=route.type.name,
        effectiveFrom=route.effective_from,
        effectiveTo=route.effective_to,
        startPointCountry=route.start_point.RU_country,
        startPointName=route.start_point.RU_city,
        endPointCountry=route.end_point.RU_country,
        endPointName=route.end_point.RU_city,
        comment=route.comment,
        timetable=route.timetable,
        container_transfer_terms=route.container_transfer_terms,
        container_shipment_terms=route.container_shipment_terms,
        container_owner=route.container_owner,
        prices=prices,
    )


def _services_from_segment(route: RouteModel, segment_id: int | str) -> list[ServiceItem]:
    return [
        ServiceItem(
            segment_id=segment_id,
            name=s.service.name,
            description=s.service.description,
            hint=s.service.hint,
            currency=s.currency,
            price=s.price,
            checked=s.service.default,
            mandatory=s.service.mandatory,
        )
        for s in route.services
    ]


def _route_from_orm(
    route_and_drop: tuple[list[Base], bool],
) -> Route:
    segments_raw, may_route_be_invalid = route_and_drop
    drop_model: DropOffModel | None = None

    if isinstance(segments_raw[-1], DropOffModel) or not segments_raw[-1]:
        drop_model = segments_raw[-1]
        segments_raw = segments_raw[:-1]

    all_services: list[ServiceItem] = []
    mapped_segments: list[RouteSegment] = []

    for segment in segments_raw:
        seg = _segment_from_orm(segment)
        mapped_segments.append(seg)
        all_services.extend(_services_from_segment(segment, seg.id))

    drop: DropOffItem | None = None
    if drop_model is not None:
        drop = DropOffItem(
            price=drop_model.price,
            conversation_percents=drop_model.conversation_percents,
            currency=drop_model.currency,
        )

    return Route(
        segments=mapped_segments,
        drop=drop,
        may_be_invalid=may_route_be_invalid,
        services=all_services,
    )


def transform_routes(
    routes_and_drops: list[tuple[list[Base], bool]],
) -> list[Route]:
    return [_route_from_orm(r) for r in routes_and_drops]
