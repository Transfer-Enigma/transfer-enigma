import datetime
from unittest.mock import AsyncMock, patch

import pytest
from entrypoints.user.schemas.form_requests import CalculateFormRequest
from services.demo_transforms import apply_demo_transforms, strip_demo_fields
from services.route_calculation import calculate_routes, search_containers
from shared.context import CallerContext, ContextKind
from shared.dto.route import ContainerItem, PriceItem, RouteResult, RouteSegment


def _make_segment(company: str = "CompanyA", **overrides) -> RouteSegment:
    kwargs = dict(  # noqa: C408
        id=1,
        company=company,
        type="RAIL",
        effectiveFrom="2024-01-01",
        effectiveTo="2025-12-31",
        startPointCountry="Россия",
        startPointName="Москва",
        endPointCountry="Россия",
        endPointName="Владивосток",
        comment=None,
        timetable=None,
        container_transfer_terms="FIFO",
        container_shipment_terms="FOB",
        container_owner="COC",
        prices=[
            PriceItem(
                container=ContainerItem(
                    id=1, size=20, type="DC", weight_from=0, weight_to=28000, name="20DC"
                ),
                value=1000.0,
                currency="USD",
                conversation_percents=0,
            )
        ],
    )
    kwargs.update(overrides)
    return RouteSegment(**kwargs)


def _make_full_route(company: str = "CompanyA", segments_count: int = 1, **segment_overrides) -> RouteResult:
    segment = _make_segment(company=company, **segment_overrides)
    segments = [segment]
    if segments_count > 1:
        segments.append(_make_segment(company=company, id=2, type="SEA"))
    return RouteResult(segments=segments)


def _make_request(
    dispatch_date: datetime.date | None = None,
    dep_internal: list[int] | None = None,
    dest_internal: list[int] | None = None,
    dep_external: list[str] | None = None,
    dest_external: list[str] | None = None,
    weight: float = 20000,
    container_type: int = 20,
    head_truck: bool = False,
    tail_truck: bool = False,
) -> CalculateFormRequest:
    return CalculateFormRequest(
        dispatchDate=dispatch_date or datetime.date(2024, 6, 15),
        departureInternalIds=dep_internal or [1],
        destinationInternalIds=dest_internal or [2],
        departureExternalIds=dep_external or [],
        destinationExternalIds=dest_external or [],
        cargoWeight=weight,
        containerType=container_type,
        headTruck=head_truck,
        tailTruck=tail_truck,
    )


# ──────────────────────────────────────────────
# Service-level tests — calculate_routes returns RouteResult dataclasses
# ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rail_only_internal():
    route = _make_full_route(company="CompanyA")
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(
            return_value=[ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_internal.find_paths = AsyncMock(return_value=[route])
        mock_fesco.get_containers = AsyncMock(return_value=[])
        mock_fesco.find_paths = AsyncMock(return_value=[])

        request = _make_request()
        routes, errors = await calculate_routes(request.to_calculation_request())

    assert len(routes) == 1
    assert len(errors) == 0
    assert len(routes[0].segments) == 1
    assert routes[0].segments[0].company == "CompanyA"
    assert routes[0].segments[0].type == "RAIL"


@pytest.mark.asyncio
async def test_sea_only_internal():
    route = _make_full_route(company="SeaLine", type="SEA")
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(
            return_value=[ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_internal.find_paths = AsyncMock(return_value=[route])
        mock_fesco.get_containers = AsyncMock(return_value=[])
        mock_fesco.find_paths = AsyncMock(return_value=[])

        request = _make_request()
        routes, _errors = await calculate_routes(request.to_calculation_request())

    assert len(routes) == 1
    assert routes[0].segments[0].type == "SEA"


@pytest.mark.asyncio
async def test_no_routes_found():
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(
            return_value=[ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_internal.find_paths = AsyncMock(return_value=[])
        mock_fesco.get_containers = AsyncMock(return_value=[])
        mock_fesco.find_paths = AsyncMock(return_value=[])

        request = _make_request()
        routes, _errors = await calculate_routes(request.to_calculation_request())

    assert len(routes) == 0


@pytest.mark.asyncio
async def test_no_matching_containers():
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(return_value=[])
        mock_internal.find_paths = AsyncMock(return_value=[])
        mock_fesco.get_containers = AsyncMock(return_value=[])
        mock_fesco.find_paths = AsyncMock(return_value=[])

        request = _make_request()
        routes, _errors = await calculate_routes(request.to_calculation_request())

    assert len(routes) == 0


@pytest.mark.asyncio
async def test_multiple_internal_pairs():
    route_a = _make_full_route(company="CompanyA")
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(
            return_value=[ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_internal.find_paths = AsyncMock(return_value=[route_a])
        mock_fesco.get_containers = AsyncMock(return_value=[])
        mock_fesco.find_paths = AsyncMock(return_value=[])

        request = _make_request(dep_internal=[1, 3], dest_internal=[2, 4])
        routes, _errors = await calculate_routes(request.to_calculation_request())

    assert len(routes) >= 1


@pytest.mark.asyncio
async def test_fesco_external_source():
    route = _make_full_route(company="FESCO")
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(return_value=[])
        mock_internal.find_paths = AsyncMock(return_value=[])
        mock_fesco.get_containers = AsyncMock(
            return_value=[ContainerItem(id="f1", size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_fesco.find_paths = AsyncMock(return_value=[route])

        request = _make_request(dep_external=["EXT1"], dest_external=["EXT2"])
        routes, _errors = await calculate_routes(request.to_calculation_request())

    assert len(routes) == 1
    assert routes[0].segments[0].company == "FESCO"


@pytest.mark.asyncio
async def test_mixed_internal_and_external():
    route_int = _make_full_route(company="CompanyA")
    route_ext = _make_full_route(company="FESCO")
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(
            return_value=[ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_internal.find_paths = AsyncMock(return_value=[route_int])
        mock_fesco.get_containers = AsyncMock(
            return_value=[ContainerItem(id="f1", size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_fesco.find_paths = AsyncMock(return_value=[route_ext])

        request = _make_request(
            dep_internal=[1], dest_internal=[2], dep_external=["EXT1"], dest_external=["EXT2"]
        )
        routes, _errors = await calculate_routes(request.to_calculation_request())

    assert len(routes) == 2
    companies = {seg.company for route_res in routes for seg in route_res.segments}
    assert "CompanyA" in companies
    assert "FESCO" in companies


@pytest.mark.asyncio
async def test_fesco_api_error_does_not_break_all():
    route_int = _make_full_route(company="CompanyA")
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(
            return_value=[ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_internal.find_paths = AsyncMock(return_value=[route_int])
        mock_fesco.get_containers = AsyncMock(side_effect=Exception("FESCO timeout"))
        mock_fesco.find_paths = AsyncMock(side_effect=Exception("FESCO timeout"))

        request = _make_request(
            dep_internal=[1], dest_internal=[2], dep_external=["EXT1"], dest_external=["EXT2"]
        )
        routes, errors = await calculate_routes(request.to_calculation_request())

    assert len(routes) == 1
    assert routes[0].segments[0].company == "CompanyA"
    assert len(errors) == 1


@pytest.mark.asyncio
async def test_external_only_without_internal():
    route = _make_full_route(company="FESCO")
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(return_value=[])
        mock_internal.find_paths = AsyncMock(return_value=[])
        mock_fesco.get_containers = AsyncMock(
            return_value=[ContainerItem(id="f1", size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_fesco.find_paths = AsyncMock(return_value=[route])

        request = _make_request(dep_internal=[], dest_internal=[], dep_external=["EXT1"], dest_external=["EXT2"])
        routes, errors = await calculate_routes(request.to_calculation_request())

    assert len(routes) == 1
    assert errors == []


@pytest.mark.asyncio
async def test_empty_ids_lists_returns_empty():
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(return_value=[])
        mock_internal.find_paths = AsyncMock(return_value=[])
        mock_fesco.get_containers = AsyncMock(return_value=[])
        mock_fesco.find_paths = AsyncMock(return_value=[])

        request = _make_request(dep_internal=[], dest_internal=[], dep_external=[], dest_external=[])
        routes, errors = await calculate_routes(request.to_calculation_request())

    assert routes == []
    assert errors == []


@pytest.mark.asyncio
async def test_container_fetch_fails_gracefully():
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(side_effect=Exception("DB timeout"))
        mock_internal.find_paths = AsyncMock(return_value=[])
        mock_fesco.get_containers = AsyncMock(return_value=[])
        mock_fesco.find_paths = AsyncMock(return_value=[])

        request = _make_request()
        routes, errors = await calculate_routes(request.to_calculation_request())

    assert len(routes) == 0
    assert len(errors) == 1


# ──────────────────────────────────────────────
# Handler-level tests — format conversion + demo transforms
# ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apply_demo_transforms_strips_company(caller_context):
    seg = _make_segment(company="CompanyA")
    route = RouteResult(segments=[seg])
    caller_context(CallerContext(kind=ContextKind.DEMO, excluded_fields=["company"]))

    await apply_demo_transforms(route)

    assert route.segments[0].company is None


@pytest.mark.asyncio
async def test_apply_demo_transforms_does_not_strip_for_non_demo(caller_context):
    seg = _make_segment(company="CompanyA")
    route = RouteResult(segments=[seg])
    caller_context(CallerContext(kind=ContextKind.ADMIN))

    await apply_demo_transforms(route)

    assert route.segments[0].company == "CompanyA"


@pytest.mark.asyncio
@patch("services.profit.get_rates", new_callable=AsyncMock)
async def test_apply_demo_transforms_with_profit(mock_rates, caller_context):
    mock_rates.return_value = ({"RUB": 1, "USD": 90, "EUR": 100}, datetime.date.today())
    seg = _make_segment(company="CompanyA", type="sea")
    route = RouteResult(segments=[seg])
    caller_context(CallerContext(
        kind=ContextKind.DEMO,
        excluded_fields=["company"],
        sea_profit=100.0,
        sea_profit_currency="USD",
    ))

    await apply_demo_transforms(route)

    assert route.segments[0].company is None


@pytest.mark.asyncio
@patch("services.profit.get_rates", new_callable=AsyncMock)
async def test_apply_demo_transforms_with_profit_and_rail(mock_rates, caller_context):
    mock_rates.return_value = ({"RUB": 1, "USD": 90, "EUR": 100}, datetime.date.today())
    seg = _make_segment(company="CompanyA", type="rail")
    route = RouteResult(segments=[seg])
    caller_context(CallerContext(
        kind=ContextKind.DEMO,
        excluded_fields=["company"],
        rail_profit=50.0,
        rail_profit_currency="USD",
    ))

    await apply_demo_transforms(route)

    assert route.segments[0].company is None


def test_strip_demo_fields_empty_segments():
    segments = []
    strip_demo_fields(segments, ["company"])
    assert segments == []


@pytest.mark.asyncio
async def test_truck_start_point_forwarded_to_internal():
    route = _make_full_route()
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(
            return_value=[ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_internal.find_paths = AsyncMock(return_value=[route])
        mock_fesco.get_containers = AsyncMock(return_value=[])
        mock_fesco.find_paths = AsyncMock(return_value=[])

        request = _make_request(head_truck=True)
        await calculate_routes(request.to_calculation_request())

    mock_internal.find_paths.assert_called_once()
    query = mock_internal.find_paths.call_args.args[0]
    assert query.head_truck is True
    assert query.tail_truck is False


@pytest.mark.asyncio
async def test_truck_end_point_forwarded_to_internal():
    route = _make_full_route()
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(
            return_value=[ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_internal.find_paths = AsyncMock(return_value=[route])
        mock_fesco.get_containers = AsyncMock(return_value=[])
        mock_fesco.find_paths = AsyncMock(return_value=[])

        request = _make_request(tail_truck=True)
        await calculate_routes(request.to_calculation_request())

    mock_internal.find_paths.assert_called_once()
    query = mock_internal.find_paths.call_args.args[0]
    assert query.head_truck is False
    assert query.tail_truck is True


@pytest.mark.asyncio
async def test_no_truck_params_by_default():
    route = _make_full_route()
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(
            return_value=[ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_internal.find_paths = AsyncMock(return_value=[route])
        mock_fesco.get_containers = AsyncMock(return_value=[])
        mock_fesco.find_paths = AsyncMock(return_value=[])

        request = _make_request()
        await calculate_routes(request.to_calculation_request())

    mock_internal.find_paths.assert_called_once()
    query = mock_internal.find_paths.call_args.args[0]
    assert query.head_truck is False
    assert query.tail_truck is False


@pytest.mark.asyncio
async def test_both_truck_params_forwarded_to_external():
    route = _make_full_route()
    with (
        patch("services.route_calculation.internal_source") as mock_internal,
        patch("services.route_calculation.fesco_source") as mock_fesco,
    ):
        mock_internal.get_containers = AsyncMock(return_value=[])
        mock_internal.find_paths = AsyncMock(return_value=[])
        mock_fesco.get_containers = AsyncMock(
            return_value=[ContainerItem(id="f1", size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
        )
        mock_fesco.find_paths = AsyncMock(return_value=[route])

        request = _make_request(
            dep_external=["EXT1"], dest_external=["EXT2"],
            head_truck=True, tail_truck=True,
        )
        await calculate_routes(request.to_calculation_request())

    mock_fesco.find_paths.assert_called_once()
    query = mock_fesco.find_paths.call_args.args[0]
    assert query.head_truck is True
    assert query.tail_truck is True


class TestSearchContainers:
    def _ids(self, containers, weight, size):
        return [container.id for container in search_containers(containers, weight, size)]

    def test_finds_matching_containers(self):
        containers = [
            ContainerItem(id=1, size=20, type="DC", weight_from=0, weight_to=28000, name="20DC"),
            ContainerItem(id=2, size=20, type="DC", weight_from=28001, weight_to=50000, name="20DC"),
        ]

        assert self._ids(containers, weight=20000, size=20) == [1]
        assert self._ids(containers, weight=30000, size=20) == [2]

    def test_container_without_weight_to_is_accepted(self):
        containers = [
            ContainerItem(id=1, size=20, type="DC", weight_from=0, weight_to=None, name="20DC"),
        ]

        assert self._ids(containers, weight=99999, size=20) == [1]

    def test_no_match_returns_empty(self):
        containers = [
            ContainerItem(id=1, size=20, type="DC", weight_from=0, weight_to=28000, name="20DC"),
        ]

        assert self._ids(containers, weight=99999, size=20) == []

    def test_wrong_size_returns_empty(self):
        containers = [
            ContainerItem(id=1, size=20, type="DC", weight_from=0, weight_to=28000, name="20DC"),
        ]

        assert self._ids(containers, weight=20000, size=40) == []

    def test_edges(self):
        containers = [
            ContainerItem(id=1, size=20, type="DC", weight_from=0, weight_to=28000, name="20DC"),
            ContainerItem(id=2, size=20, type="DC", weight_from=28001, weight_to=50000, name="20DC"),
            ContainerItem(id=3, size=40, type="DC", weight_from=0, weight_to=28000, name="40DC"),
            ContainerItem(id=4, size=40, type="DC", weight_from=28001, weight_to=50000, name="40DC"),
        ]

        assert self._ids(containers, weight=0, size=20) == [1]
        assert self._ids(containers, weight=28000, size=20) == [1]
        assert self._ids(containers, weight=28001, size=20) == [2]
        assert self._ids(containers, weight=50000, size=40) == [4]
        assert self._ids(containers, weight=50001, size=40) == []
        assert self._ids(containers, weight=20000, size=30) == []
        assert self._ids(containers, weight=-1, size=20) == []
