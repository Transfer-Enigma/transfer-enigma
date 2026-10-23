from unittest.mock import AsyncMock, patch

import pytest
from services.route_calculation import _strip_demo_fields
from shared.dto.route import RouteSegment


class TestStripDemoFields:
    def test_removes_company_from_segments(self):
        seg1 = _make_segment(company="CompanyA")
        seg2 = _make_segment(company="CompanyB", id=2)
        routes = [([seg1, seg2], None, False, [])]
        _strip_demo_fields(routes, ["company"])
        assert seg1.company is None
        assert seg2.company is None

    def test_preserves_other_fields(self):
        seg = _make_segment(company="CompanyA")
        routes = [([seg], None, False, [])]
        _strip_demo_fields(routes, ["company"])
        assert seg.company is None
        assert seg.id == 1
        assert seg.type == "RAIL"

    def test_multiple_routes(self):
        seg1 = _make_segment(company="Co1")
        seg2 = _make_segment(company="Co2", id=2)
        routes = [
            ([seg1], None, False, []),
            ([seg2], None, False, []),
        ]
        _strip_demo_fields(routes, ["company"])
        assert seg1.company is None
        assert seg2.company is None


def _make_segment(company: str = "CompanyA", **kwargs) -> RouteSegment:
    return RouteSegment(
        id=kwargs.get("id", 1),
        company=company,
        type=kwargs.get("type", "RAIL"),
        effectiveFrom="2024-01-01",
        effectiveTo="2025-12-31",
        startPointCountry="RU",
        startPointName="Moscow",
        endPointCountry="CN",
        endPointName="Shanghai",
    )


@pytest.mark.asyncio
async def test_get_auth_context_with_demo_header(sqlite_db):
    from entrypoints.user.dependencies.auth_context import get_auth_context

    demo_guest = AsyncMock()
    demo_guest.sea_profit = 50.0
    demo_guest.sea_profit_currency = "USD"
    demo_guest.rail_profit = 30.0
    demo_guest.rail_profit_currency = "USD"

    with (
        patch("entrypoints.user.dependencies.auth_context.get_demo_guest_by_uid", return_value=demo_guest),
        patch("entrypoints.user.dependencies.auth_context.get_database", return_value=sqlite_db),
    ):
        mock_request = AsyncMock()
        mock_request.headers.get = lambda key, default=None: "demo-uid-123" if key == "X-Demo-User-UID" else default

        mock_auth = AsyncMock()
        settings = AsyncMock()
        settings.DISABLE_USER_AUTH_CHECK = True

        result = await get_auth_context(
            request=mock_request,
            authorization=mock_auth,
            db=sqlite_db,
            settings=settings,
        )

    assert result.is_demo is True
    assert result.demo_uid == "demo-uid-123"
    assert result.sea_profit == 50.0
    assert result.rail_profit == 30.0


@pytest.mark.asyncio
async def test_get_auth_context_without_demo_header(sqlite_db):
    from entrypoints.user.dependencies.auth_context import get_auth_context

    with (
        patch("entrypoints.user.dependencies.auth_context.request_auth", return_value=None),
    ):
        mock_request = AsyncMock()
        mock_request.headers.get = lambda key, default=None: None

        mock_auth = AsyncMock()
        settings = AsyncMock()
        settings.DISABLE_USER_AUTH_CHECK = True

        result = await get_auth_context(
            request=mock_request,
            authorization=mock_auth,
            db=sqlite_db,
            settings=settings,
        )

    assert result.is_demo is False
    assert result.demo_uid is None
    assert result.sea_profit == 0.0
    assert result.rail_profit == 0.0


@pytest.mark.asyncio
async def test_get_auth_context_invalid_demo_uid(sqlite_db):
    from entrypoints.user.dependencies.auth_context import get_auth_context

    with (
        patch("entrypoints.user.dependencies.auth_context.get_demo_guest_by_uid", return_value=None),
        patch("entrypoints.user.dependencies.auth_context.get_database", return_value=sqlite_db),
    ):
        mock_request = AsyncMock()
        mock_request.headers.get = lambda key, default=None: "invalid-uid" if key == "X-Demo-User-UID" else default

        mock_auth = AsyncMock()
        settings = AsyncMock()
        settings.DISABLE_USER_AUTH_CHECK = True

        result = await get_auth_context(
            request=mock_request,
            authorization=mock_auth,
            db=sqlite_db,
            settings=settings,
        )

    assert result.is_demo is False
    assert result.demo_uid is None


@pytest.mark.asyncio
async def test_strip_demo_fields_no_routes():
    from services.route_calculation import _strip_demo_fields

    routes = []
    _strip_demo_fields(routes)
    assert routes == []


@pytest.mark.asyncio
async def test_strip_demo_fields_empty_segments_list():
    from services.route_calculation import _strip_demo_fields

    routes = [([], None, False, [])]
    _strip_demo_fields(routes)
    assert routes[0][0] == []
