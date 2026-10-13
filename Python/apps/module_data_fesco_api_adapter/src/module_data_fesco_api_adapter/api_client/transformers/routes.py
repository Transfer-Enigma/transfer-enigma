import logging
from collections.abc import Iterable

from module_shared.models.route import PriceItem, RouteResult, RouteSegment, ServiceItem

from .containers import transform_container

logger = logging.getLogger(__name__)

_segment_types = {
    1: "rail",
    2: "sea",
    3: "truck",
}


def _check_currency(currency):
    return "RUB" if currency == "RUR" else currency


def transform_service(service: dict) -> ServiceItem | None:
    if service.get("group"):
        if not service.get("items"):
            logger.warning("FESCO: skipping service group — no items")
            return None

        service = service["items"][0]

    if "SegmentUID" not in service or "ServiceName" not in service:
        logger.warning("FESCO: skipping service — missing SegmentUID/ServiceName")
        return None

    return ServiceItem(
        segment_id=service["SegmentUID"],
        name=(
            service["ServiceType"][0]["ServiceTypeName"]
            if service.get("ServiceType")
            else service["ServiceName"]
        ),
        description=service["ServiceName"],
        hint=service.get("ServiceComment") or None,
        checked=service.get("checked", False),
        mandatory=service.get("Default", False) and service.get("InclMainServicePrice", False),
        currency=service["ContPrice"][0]["Currency"] if service.get("ContPrice") else None,
        price=(
            service["ContPrice"][0]["Price"] * service["ContPrice"][0]["Quantity"]
            if service.get("ContPrice")
            else None
        ),
    )


def transform_route(route: dict) -> RouteResult:
    services = [item for item in map(transform_service, route.get("Services", [])) if item]
    container_descriptor = transform_container(route["Containers"][0])
    segments: list[RouteSegment] = []

    for segm in route.get("Segments", []):
        cont_data = segm.get("Containers", [{}])[0]
        seg_type = _segment_types.get(segm.get("SegmentType"))

        seg = RouteSegment(
            id=segm["SegmentUID"],
            company="FESCO",
            type=seg_type,
            effectiveFrom=route["DateFrom"],
            effectiveTo=route["DateTo"],
            startPointCountry=segm["BeginCountryName"],
            startPointName=segm["BeginLocName"],
            endPointCountry=segm["FinishCountryName"],
            endPointName=segm["FinishLocName"],
            container_transfer_terms=route["BeginCond"] + route["FinishCond"] if seg_type == "sea" else None,
            container_owner="COC",
            prices=[PriceItem(
                value=cont_data.get("Price", 0),
                currency=_check_currency(cont_data.get("Currency", "USD")),
                container=container_descriptor,
            )],
        )
        segments.append(seg)

    return RouteResult(segments=segments, services=services)


def transform_routes(routes: list[dict]) -> Iterable[RouteResult]:
    return map(transform_route, routes)
