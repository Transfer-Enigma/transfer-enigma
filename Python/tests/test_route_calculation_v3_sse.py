import datetime
from unittest.mock import AsyncMock, patch

from fastapi.sse import ServerSentEvent

import pytest
from backend_user.api.v3.routes.post import _sse_generator
from backend_user.dependencies.auth_context import AuthContext
from backend_user.schemas.errors import RouteError
from backend_user.schemas.form_requests import CalculateFormRequest
from backend_user.services.route_calculation import calculate_routes_stream
from module_shared.models.route import ContainerItem, PriceItem, Route, RouteSegment


def _make_segment(company: str = "CompanyA", **overrides) -> RouteSegment:
    kwargs = {
        "id": 1,
        "company": company,
        "type": "RAIL",
        "effectiveFrom": "2024-01-01",
        "effectiveTo": "2025-12-31",
        "startPointCountry": "Россия",
        "startPointName": "Москва",
        "endPointCountry": "Россия",
        "endPointName": "Владивосток",
        "comment": None,
        "timetable": None,
        "container_transfer_terms": "FIFO",
        "container_shipment_terms": "FOB",
        "container_owner": "COC",
        "prices": [
            PriceItem(
                container=ContainerItem(
                    id=1, size=20, type="DC", weight_from=0, weight_to=28000, name="20DC"
                ),
                value=1000.0,
                currency="USD",
                conversation_percents=0,
            )
        ],
    }
    kwargs.update(overrides)
    return RouteSegment(**kwargs)


def _make_full_route(company: str = "CompanyA", segments_count: int = 1, **segment_overrides) -> Route:
    segment = _make_segment(company=company, **segment_overrides)
    segments = [segment]
    if segments_count > 1:
        segments.append(_make_segment(company=company, id=2, type="SEA"))
    return Route(segments=segments)


def _make_request(
    dispatch_date=None,
    dep_internal=None,
    dest_internal=None,
    dep_external=None,
    dest_external=None,
    weight=20000,
    container_type=20,
) -> CalculateFormRequest:
    from datetime import date
    return CalculateFormRequest(
        dispatchDate=dispatch_date or date(2024, 6, 15),
        departureInternalIds=dep_internal or [1],
        destinationInternalIds=dest_internal or [2],
        departureExternalIds=dep_external or [],
        destinationExternalIds=dest_external or [],
        cargoWeight=weight,
        containerType=container_type,
    )


class TestSSEGenerator:
    @pytest.mark.asyncio
    async def test_sse_streams_routes(self):
        route1 = _make_full_route(company="CompanyA")
        route2 = _make_full_route(company="CompanyB")

        with patch("backend_user.api.v3.routes.post.calculate_routes_stream") as mock_stream:
            async def mock_gen(request):
                yield route1
                yield route2

            mock_stream.side_effect = mock_gen

            auth = AuthContext(is_demo=False)
            request = _make_request()

            events: list[ServerSentEvent] = []
            async for event in _sse_generator(request, auth):
                events.append(event)

            assert len(events) == 2
            assert events[0].event == "route"
            assert events[1].event == "route"
            assert events[0].data is route1
            assert events[1].data is route2
            assert events[0].id == "0"
            assert events[1].id == "1"

    @pytest.mark.asyncio
    async def test_sse_streams_errors(self):
        error = RouteError(error_type="ValueError", error_text="Invalid data", source="internal")

        with patch("backend_user.api.v3.routes.post.calculate_routes_stream") as mock_stream:
            async def mock_gen(request):
                yield error

            mock_stream.side_effect = mock_gen

            auth = AuthContext(is_demo=False)
            request = _make_request()

            events: list[ServerSentEvent] = []
            async for event in _sse_generator(request, auth):
                events.append(event)

            assert len(events) == 1
            assert events[0].event == "error"
            assert events[0].data is error

    @pytest.mark.asyncio
    async def test_sse_mixed_routes_and_errors(self):
        route = _make_full_route(company="CompanyA")
        error = RouteError(error_type="TimeoutError", error_text="FESCO timeout", source="external")

        with patch("backend_user.api.v3.routes.post.calculate_routes_stream") as mock_stream:
            async def mock_gen(request):
                yield route
                yield error

            mock_stream.side_effect = mock_gen

            auth = AuthContext(is_demo=False)
            request = _make_request()

            events: list[ServerSentEvent] = []
            async for event in _sse_generator(request, auth):
                events.append(event)

            assert len(events) == 2
            assert events[0].event == "route"
            assert events[1].event == "error"
            assert events[0].data is route
            assert events[1].data is error
            assert events[0].id == "0"
            assert events[1].id == "1"

    @pytest.mark.asyncio
    async def test_sse_last_event_id(self):
        route = _make_full_route(company="CompanyA")

        with patch("backend_user.api.v3.routes.post.calculate_routes_stream") as mock_stream:
            async def mock_gen(request):
                yield route

            mock_stream.side_effect = mock_gen

            auth = AuthContext(is_demo=False)
            request = _make_request()

            events: list[ServerSentEvent] = []
            async for event in _sse_generator(request, auth, last_event_id=5):
                events.append(event)

            assert len(events) == 1
            assert events[0].id == "6"

    @pytest.mark.asyncio
    async def test_sse_demo_transforms_strips_company(self):
        route = _make_full_route(company="CompanyA")
        auth = AuthContext(is_demo=True)

        with patch("backend_user.api.v3.routes.post.calculate_routes_stream") as mock_stream:
            async def mock_gen(request):
                yield route

            mock_stream.side_effect = mock_gen

            request = _make_request()
            events: list[ServerSentEvent] = []
            async for event in _sse_generator(request, auth):
                events.append(event)

            assert events[0].data.segments[0].company is None

    @pytest.mark.asyncio
    async def test_sse_demo_transforms_does_not_strip_for_non_demo(self):
        route = _make_full_route(company="CompanyA")
        auth = AuthContext(is_demo=False)

        with patch("backend_user.api.v3.routes.post.calculate_routes_stream") as mock_stream:
            async def mock_gen(request):
                yield route

            mock_stream.side_effect = mock_gen

            request = _make_request()
            events: list[ServerSentEvent] = []
            async for event in _sse_generator(request, auth):
                events.append(event)

            assert events[0].data.segments[0].company == "CompanyA"

    @pytest.mark.asyncio
    async def test_sse_demo_transforms_with_profit(self):
        route = _make_full_route(company="CompanyA", type="sea")
        auth = AuthContext(is_demo=True, sea_profit=100.0, sea_profit_currency="USD")

        mock_rates = ({"RUB": 1, "USD": 90, "EUR": 100}, datetime.date.today())
        with patch("backend_user.api.v3.routes.post.calculate_routes_stream") as mock_stream:
            with patch("backend_user.services.profit.get_rates", return_value=mock_rates):
                async def mock_gen(request):
                    yield route

                mock_stream.side_effect = mock_gen

                request = _make_request()
                events: list[ServerSentEvent] = []
                async for event in _sse_generator(request, auth):
                    events.append(event)

            assert events[0].data.segments[0].company is None
            price = events[0].data.segments[0].prices[0]
            assert price.value == 1100.0

    @pytest.mark.asyncio
    async def test_sse_empty_results(self):
        with patch("backend_user.api.v3.routes.post.calculate_routes_stream") as mock_stream:
            async def mock_gen(request):
                return
                yield

            mock_stream.side_effect = mock_gen

            auth = AuthContext(is_demo=False)
            request = _make_request()

            events: list[ServerSentEvent] = []
            async for event in _sse_generator(request, auth):
                events.append(event)

            assert len(events) == 0


class TestCalculateRoutesStream:
    @pytest.mark.asyncio
    async def test_stream_yields_routes_from_internal(self):
        route1 = _make_full_route(company="CompanyA")
        route2 = _make_full_route(company="CompanyB")

        with (
            patch("backend_user.services.route_calculation.aggregators") as mock_agg,
            patch("backend_user.services.route_calculation.api_client") as mock_fesco,
        ):
            mock_agg.get_containers = AsyncMock(
                return_value=[ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
            )
            mock_agg.search_container_ids = lambda containers, weight, size: [1]
            mock_agg.find_all_paths = AsyncMock(return_value=[route1, route2])
            mock_fesco.get_containers = AsyncMock(return_value=[])
            mock_fesco.search_container_ids = lambda containers, weight, size: []
            mock_fesco.find_all_paths = AsyncMock(return_value=[])

            request = _make_request(dep_internal=[1, 3], dest_internal=[2, 4])

            results = []
            async for item in calculate_routes_stream(request):
                results.append(item)

            assert len(results) == 8
            assert all(isinstance(r, Route) for r in results)
            companies = {r.segments[0].company for r in results}
            assert "CompanyA" in companies
            assert "CompanyB" in companies

    @pytest.mark.asyncio
    async def test_stream_yields_errors(self):
        with (
            patch("backend_user.services.route_calculation.aggregators") as mock_agg,
            patch("backend_user.services.route_calculation.api_client") as mock_fesco,
        ):
            mock_agg.get_containers = AsyncMock(
                return_value=[ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
            )
            mock_agg.search_container_ids = lambda containers, weight, size: [1]
            mock_agg.find_all_paths = AsyncMock(side_effect=Exception("DB timeout"))
            mock_fesco.get_containers = AsyncMock(return_value=[])
            mock_fesco.search_container_ids = lambda containers, weight, size: []
            mock_fesco.find_all_paths = AsyncMock(return_value=[])

            request = _make_request()

            results = []
            async for item in calculate_routes_stream(request):
                results.append(item)

            assert len(results) == 1
            assert isinstance(results[0], RouteError)
            assert results[0].error_type == "Exception"
            assert results[0].source == "internal"

    @pytest.mark.asyncio
    async def test_stream_mixed_internal_and_external(self):
        route_int = _make_full_route(company="CompanyA")
        route_ext = _make_full_route(company="FESCO")

        with (
            patch("backend_user.services.route_calculation.aggregators") as mock_agg,
            patch("backend_user.services.route_calculation.api_client") as mock_fesco,
        ):
            mock_agg.get_containers = AsyncMock(
                return_value=[ContainerItem(id=1, size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
            )
            mock_agg.search_container_ids = lambda containers, weight, size: [1]
            mock_agg.find_all_paths = AsyncMock(return_value=[route_int])
            mock_fesco.get_containers = AsyncMock(
                return_value=[ContainerItem(id="f1", size=20, weight_from=0, weight_to=28000, type="DC", name="20DC")]
            )
            mock_fesco.search_container_ids = lambda containers, weight, size: ["f1"]
            mock_fesco.find_all_paths = AsyncMock(return_value=[route_ext])

            request = _make_request(dep_internal=[1], dest_internal=[2], dep_external=["EXT1"], dest_external=["EXT2"])

            results = []
            async for item in calculate_routes_stream(request):
                results.append(item)

            assert len(results) == 2
            companies = {r.segments[0].company for r in results}
            assert "CompanyA" in companies
            assert "FESCO" in companies

    @pytest.mark.asyncio
    async def test_stream_empty_ids(self):
        with (
            patch("backend_user.services.route_calculation.aggregators") as mock_agg,
            patch("backend_user.services.route_calculation.api_client") as mock_fesco,
        ):
            mock_agg.get_containers = AsyncMock(return_value=[])
            mock_agg.search_container_ids = lambda containers, weight, size: []
            mock_agg.find_all_paths = AsyncMock(return_value=[])
            mock_fesco.get_containers = AsyncMock(return_value=[])
            mock_fesco.search_container_ids = lambda containers, weight, size: []
            mock_fesco.find_all_paths = AsyncMock(return_value=[])

            request = _make_request(dep_internal=[], dest_internal=[], dep_external=[], dest_external=[])

            results = []
            async for item in calculate_routes_stream(request):
                results.append(item)

            assert len(results) == 0
