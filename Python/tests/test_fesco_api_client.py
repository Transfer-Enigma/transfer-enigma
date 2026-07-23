import datetime
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from module_data_fesco_api_adapter.api_client.containers import get_containers, search_container_ids
from module_data_fesco_api_adapter.api_client.points import (
    get_departure_points_by_date,
    get_destination_points_by_date,
)
from module_data_fesco_api_adapter.api_client.routes import find_all_paths
from module_data_fesco_api_adapter.api_client.transformers.containers import (
    transform_container,
    transform_containers,
)
from module_data_fesco_api_adapter.api_client.transformers.points import (
    _transform_point,
    transform_points,
)
from module_data_fesco_api_adapter.api_client.transformers.routes import (
    transform_route,
    transform_routes,
    transform_service,
)
from module_shared.models.route import ContainerItem


def _mock_redis(get_return=None):
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=get_return)
    mock_redis.set = AsyncMock()
    return mock_redis


# ============================================================
# Container transformer tests
# ============================================================


class TestTransformContainer:
    def test_full_weight_range(self):
        container = {
            "ContainerCode": "20DC1",
            "ContainerNameEng": "(20'DC) 0-28t",
        }
        result = transform_container(container)

        assert result.id == "20DC1"
        assert result.size == 20
        assert result.type == "DC"
        assert result.weight_from == 0
        assert result.weight_to == 28
        assert result.name == "20'DC 0-28t"

    def test_single_weight(self):
        container = {
            "ContainerCode": "40HC1",
            "ContainerNameEng": "(40'HC) 28t",
        }
        result = transform_container(container)

        assert result.id == "40HC1"
        assert result.size == 40
        assert result.type == "HC"
        assert result.weight_from == 0
        assert result.weight_to == 28

    def test_no_weight(self):
        container = {
            "ContainerCode": "20DC2",
            "ContainerNameEng": "(20'DC)",
        }
        result = transform_container(container)

        assert result.id == "20DC2"
        assert result.size == 20
        assert result.type == "DC"
        assert result.weight_from is None
        assert result.weight_to is None
        assert result.name == "20'DC"

    def test_unparseable_name_returns_none(self):
        container = {
            "ContainerCode": "X1",
            "ContainerNameEng": "NON STANDARD FORMAT",
        }
        result = transform_container(container)
        assert result is None


class TestTransformContainers:
    def test_sort_by_size_then_weight(self):
        raw = [
            {"ContainerCode": "3", "ContainerNameEng": "(20'DC) 0-50t"},
            {"ContainerCode": "1", "ContainerNameEng": "(40'DC) 0-28t"},
            {"ContainerCode": "2", "ContainerNameEng": "(20'DC) 0-28t"},
        ]
        result = transform_containers(raw)

        assert [c.id for c in result] == ["2", "3", "1"]


# ============================================================
# Service transformer tests
# ============================================================


class TestTransformService:
    def test_full_service(self):
        service = {
            "SegmentUID": "seg1",
            "ServiceName": "Customs clearance",
            "ServiceType": [{"ServiceTypeName": "Customs"}],
            "ServiceComment": "Additional docs required",
            "ContPrice": [{"Currency": "USD", "Price": 200.0, "Quantity": 1}],
            "checked": True,
            "Default": True,
            "InclMainServicePrice": True,
        }
        result = transform_service(service)

        assert result.segment_id == "seg1"
        assert result.name == "Customs"
        assert result.description == "Customs clearance"
        assert result.hint == "Additional docs required"
        assert result.currency == "USD"
        assert result.price == 200.0
        assert result.checked is True
        assert result.mandatory is True

    def test_service_with_group(self):
        service = {
            "group": True,
            "items": [
                {
                    "SegmentUID": "seg2",
                    "ServiceName": "Insurance",
                    "ServiceType": [{"ServiceTypeName": "Insurance"}],
                    "ContPrice": [{"Currency": "USD", "Price": 50.0, "Quantity": 2}],
                    "checked": False,
                }
            ],
        }
        result = transform_service(service)

        assert result.segment_id == "seg2"
        assert result.name == "Insurance"
        assert result.price == 100.0

    def test_service_group_without_items_returns_none(self):
        service = {"group": True, "items": []}
        result = transform_service(service)
        assert result is None

    def test_missing_segmentuid_returns_none(self):
        service = {"ServiceName": "No UID"}
        result = transform_service(service)
        assert result is None

    def test_missing_servicename_returns_none(self):
        service = {"SegmentUID": "s1"}
        result = transform_service(service)
        assert result is None

    def test_without_contprice(self):
        service = {
            "SegmentUID": "seg3",
            "ServiceName": "Free service",
        }
        result = transform_service(service)

        assert result.segment_id == "seg3"
        assert result.currency is None
        assert result.price is None

    def test_without_servicetype(self):
        service = {
            "SegmentUID": "seg4",
            "ServiceName": "Simple service",
        }
        result = transform_service(service)

        assert result.name == "Simple service"


# ============================================================
# Route transformer tests
# ============================================================


class TestTransformRoute:
    def test_rail_segment(self):
        route = {
            "DateFrom": "2024-01-01T00:00:00",
            "DateTo": "2024-12-31T00:00:00",
            "BeginCond": "",
            "FinishCond": "",
            "Containers": [
                {"ContainerCode": "20DC1", "ContainerNameEng": "(20'DC) 0-28t"}
            ],
            "Services": [],
            "Segments": [
                {
                    "SegmentUID": "seg1",
                    "SegmentType": 1,
                    "BeginCountryName": "Россия",
                    "BeginLocName": "Москва",
                    "FinishCountryName": "Россия",
                    "FinishLocName": "Владивосток",
                    "Containers": [{"Price": 1500.0, "Currency": "USD"}],
                }
            ],
        }
        result = transform_route(route)

        assert len(result.segments) == 1
        seg = result.segments[0]
        assert seg.id == "seg1"
        assert seg.company == "FESCO"
        assert seg.type == "rail"
        assert seg.startPointName == "Москва"
        assert seg.endPointName == "Владивосток"
        assert seg.container_owner == "COC"
        assert seg.container_transfer_terms is None
        assert len(seg.prices) == 1
        assert seg.prices[0].value == 1500.0
        assert seg.prices[0].currency == "USD"

    def test_sea_segment_with_terms(self):
        route = {
            "DateFrom": "2024-06-01T00:00:00",
            "DateTo": "2024-06-30T00:00:00",
            "BeginCond": "FCL",
            "FinishCond": "FCL",
            "Containers": [
                {"ContainerCode": "40HC1", "ContainerNameEng": "(40'HC) 0-28t"}
            ],
            "Services": [],
            "Segments": [
                {
                    "SegmentUID": "seg2",
                    "SegmentType": 2,
                    "BeginCountryName": "China",
                    "BeginLocName": "Shanghai",
                    "FinishCountryName": "Russia",
                    "FinishLocName": "Vladivostok",
                    "Containers": [{"Price": 3000.0, "Currency": "USD"}],
                }
            ],
        }
        result = transform_route(route)

        seg = result.segments[0]
        assert seg.type == "sea"
        assert seg.container_transfer_terms == "FCLFCL"
        assert seg.prices[0].value == 3000.0

    def test_truck_segment_rur_to_rub(self):
        route = {
            "DateFrom": "2024-01-01T00:00:00",
            "DateTo": "2024-12-31T00:00:00",
            "BeginCond": "",
            "FinishCond": "",
            "Containers": [
                {"ContainerCode": "20DC1", "ContainerNameEng": "(20'DC) 0-28t"}
            ],
            "Services": [],
            "Segments": [
                {
                    "SegmentUID": "seg3",
                    "SegmentType": 3,
                    "BeginCountryName": "Russia",
                    "BeginLocName": "Moscow",
                    "FinishCountryName": "Russia",
                    "FinishLocName": "Saint Petersburg",
                    "Containers": [{"Price": 500.0, "Currency": "RUR"}],
                }
            ],
        }
        result = transform_route(route)

        assert result.segments[0].type == "truck"
        assert result.segments[0].prices[0].currency == "RUB"

    def test_multiple_segments(self):
        route = {
            "DateFrom": "2024-01-01T00:00:00",
            "DateTo": "2024-12-31T00:00:00",
            "BeginCond": "",
            "FinishCond": "",
            "Containers": [
                {"ContainerCode": "C1", "ContainerNameEng": "(20'DC) 0-28t"}
            ],
            "Services": [],
            "Segments": [
                {
                    "SegmentUID": "s1",
                    "SegmentType": 2,
                    "BeginCountryName": "CN",
                    "BeginLocName": "Shanghai",
                    "FinishCountryName": "RU",
                    "FinishLocName": "Vladivostok",
                    "Containers": [{"Price": 2000.0, "Currency": "USD"}],
                },
                {
                    "SegmentUID": "s2",
                    "SegmentType": 1,
                    "BeginCountryName": "RU",
                    "BeginLocName": "Vladivostok",
                    "FinishCountryName": "RU",
                    "FinishLocName": "Moscow",
                    "Containers": [{"Price": 1000.0, "Currency": "USD"}],
                },
            ],
        }
        result = transform_route(route)

        assert len(result.segments) == 2
        assert result.segments[0].type == "sea"
        assert result.segments[1].type == "rail"

    def test_with_services(self):
        route = {
            "DateFrom": "2024-01-01T00:00:00",
            "DateTo": "2024-12-31T00:00:00",
            "BeginCond": "",
            "FinishCond": "",
            "Containers": [
                {"ContainerCode": "C1", "ContainerNameEng": "(20'DC) 0-28t"}
            ],
            "Services": [
                {
                    "SegmentUID": "s1",
                    "ServiceName": "Insurance",
                    "ServiceType": [{"ServiceTypeName": "Insurance"}],
                    "ContPrice": [{"Currency": "USD", "Price": 50.0, "Quantity": 1}],
                    "checked": True,
                    "Default": False,
                    "InclMainServicePrice": False,
                }
            ],
            "Segments": [
                {
                    "SegmentUID": "s1",
                    "SegmentType": 2,
                    "BeginCountryName": "CN",
                    "BeginLocName": "Shanghai",
                    "FinishCountryName": "RU",
                    "FinishLocName": "Vladivostok",
                    "Containers": [{"Price": 2000.0, "Currency": "USD"}],
                }
            ],
        }
        result = transform_route(route)

        assert len(result.services) == 1
        assert result.services[0].name == "Insurance"
        assert result.services[0].price == 50.0

    def test_unknown_segment_type(self):
        route = {
            "DateFrom": "2024-01-01T00:00:00",
            "DateTo": "2024-12-31T00:00:00",
            "BeginCond": "",
            "FinishCond": "",
            "Containers": [
                {"ContainerCode": "C1", "ContainerNameEng": "(20'DC) 0-28t"}
            ],
            "Services": [],
            "Segments": [
                {
                    "SegmentUID": "s1",
                    "SegmentType": 99,
                    "BeginCountryName": "XX",
                    "BeginLocName": "A",
                    "FinishCountryName": "YY",
                    "FinishLocName": "B",
                    "Containers": [{"Price": 100.0, "Currency": "USD"}],
                }
            ],
        }
        result = transform_route(route)

        assert result.segments[0].type is None


class TestTransformRoutes:
    def test_multiple_routes(self):
        routes = [
            {
                "DateFrom": "2024-01-01T00:00:00",
                "DateTo": "2024-12-31T00:00:00",
                "BeginCond": "",
                "FinishCond": "",
                "Containers": [
                    {"ContainerCode": "C1", "ContainerNameEng": "(20'DC) 0-28t"}
                ],
                "Services": [],
                "Segments": [
                    {
                        "SegmentUID": "s1",
                        "SegmentType": 1,
                        "BeginCountryName": "RU",
                        "BeginLocName": "A",
                        "FinishCountryName": "RU",
                        "FinishLocName": "B",
                        "Containers": [{"Price": 100.0, "Currency": "USD"}],
                    }
                ],
            },
            {
                "DateFrom": "2024-01-01T00:00:00",
                "DateTo": "2024-12-31T00:00:00",
                "BeginCond": "",
                "FinishCond": "",
                "Containers": [
                    {"ContainerCode": "C2", "ContainerNameEng": "(40'HC) 0-28t"}
                ],
                "Services": [],
                "Segments": [
                    {
                        "SegmentUID": "s2",
                        "SegmentType": 2,
                        "BeginCountryName": "CN",
                        "BeginLocName": "C",
                        "FinishCountryName": "RU",
                        "FinishLocName": "D",
                        "Containers": [{"Price": 200.0, "Currency": "USD"}],
                    }
                ],
            },
        ]
        result = list(transform_routes(routes))

        assert len(result) == 2
        assert result[0].segments[0].type == "rail"
        assert result[1].segments[0].type == "sea"


# ============================================================
# Point transformer tests
# ============================================================


class TestTransformPoint:
    def test_ru_only(self):
        point = {
            "id": "FESCO-123",
            "name": "Москва",
            "country": "Россия",
        }
        result = _transform_point(point)

        assert result["id"] == "FESCO-123"
        assert result["company"]["id"] == "FESCO"
        assert result["translates"]["ru"]["name"] == "Москва"
        assert result["translates"]["ru"]["country"] == "Россия"

    def test_all_languages(self):
        point = {
            "id": "FESCO-456",
            "name": "Москва",
            "country": "Россия",
            "nameLatin": "Moscow",
            "countryLatin": "Russia",
            "nameCN": "莫斯科",
            "countryCN": "俄罗斯",
            "nameVN": "Moscow",
            "countryVN": "Nga",
        }
        result = _transform_point(point)

        assert result["translates"]["ru"]["name"] == "Москва"
        assert result["translates"]["en"]["name"] == "Moscow"
        assert result["translates"]["cn"]["name"] == "莫斯科"
        assert result["translates"]["vn"]["name"] == "Moscow"

    def test_default_location_returns_none(self):
        point = {
            "id": "FESCO-999",
            "name": "DEFAULT LOCATION",
            "country": "Russia",
        }
        result = _transform_point(point)
        assert result is None

    def test_empty_name_returns_none(self):
        point = {
            "id": "FESCO-000",
            "name": "",
            "country": "Russia",
        }
        result = _transform_point(point)
        assert result is None

    def test_missing_name_field_returns_none(self):
        point = {
            "id": "FESCO-111",
            "country": "Russia",
        }
        result = _transform_point(point)
        assert result is None

    def test_partial_translations(self):
        point = {
            "id": "FESCO-789",
            "name": "Владивосток",
            "country": "Россия",
            "nameLatin": "Vladivostok",
        }
        result = _transform_point(point)

        assert "ru" in result["translates"]
        assert "en" in result["translates"]
        assert "cn" not in result["translates"]
        assert result["translates"]["en"]["country"] == ""


class TestTransformPoints:
    def test_filters_invalid_points(self):
        points = [
            {"id": "1", "name": "Москва", "country": "Россия"},
            {"id": "2", "name": "DEFAULT LOCATION", "country": "Россия"},
            {"id": "3", "name": "", "country": "Россия"},
            {"id": "4", "name": "Владивосток", "country": "Россия"},
        ]
        result = list(transform_points(points))

        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "4"


# ============================================================
# HTTP client tests — mocked API response
# ============================================================

def _mock_aiohttp_session(json_data, status_ok=True):
    mock_resp = AsyncMock()
    mock_resp.json = AsyncMock(return_value=json_data)
    mock_resp.raise_for_status = MagicMock()
    if not status_ok:
        mock_resp.raise_for_status = MagicMock(side_effect=Exception("HTTP 500"))

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    return mock_session


class TestGetContainers:
    @pytest.mark.asyncio
    async def test_success(self):
        raw_data = [
            {"ContainerCode": "20DC1", "ContainerNameEng": "(20'DC) 0-28t"},
            {"ContainerCode": "40DC1", "ContainerNameEng": "(40'DC) 0-28t"},
        ]
        mock_session = _mock_aiohttp_session({"data": raw_data})
        mock_redis = _mock_redis()

        with (
            patch(
                "module_data_fesco_api_adapter.api_client.containers.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
        ):
            result = await get_containers(
                datetime.date(2024, 6, 15), "dep1", "dest1"
            )

        assert len(result) == 2
        assert result[0].size == 20
        assert result[1].size == 40

    @pytest.mark.asyncio
    async def test_empty_data(self):
        mock_session = _mock_aiohttp_session({"data": []})
        mock_redis = _mock_redis()

        with (
            patch(
                "module_data_fesco_api_adapter.api_client.containers.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
        ):
            result = await get_containers(
                datetime.date(2024, 6, 15), "dep1", "dest1"
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_http_error_raised(self):
        mock_session = _mock_aiohttp_session({}, status_ok=False)
        mock_redis = _mock_redis()

        with (
            patch(
                "module_data_fesco_api_adapter.api_client.containers.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
            pytest.raises(Exception, match="HTTP 500"),
        ):
            await get_containers(datetime.date(2024, 6, 15), "dep1", "dest1")

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        cached_data = json.dumps([
            {"id": "20DC1", "type": "DC", "size": 20, "weight_from": 0, "weight_to": 28000, "name": "20'DC 0-28t"},
            {"id": "40DC1", "type": "DC", "size": 40, "weight_from": 0, "weight_to": 28000, "name": "40'DC 0-28t"},
        ])
        mock_redis = _mock_redis(get_return=cached_data)

        with patch(
            "module_data_fesco_api_adapter.cache.get_redis",
            return_value=mock_redis,
        ):
            result = await get_containers(datetime.date(2024, 6, 15), "dep1", "dest1")

        assert len(result) == 2
        assert result[0].size == 20
        assert result[0].id == "20DC1"
        assert result[1].size == 40

    @pytest.mark.asyncio
    async def test_cache_hit_corrupt(self):
        mock_redis = _mock_redis(get_return="not-valid-json")

        mock_session = _mock_aiohttp_session({"data": []})
        with (
            patch(
                "module_data_fesco_api_adapter.api_client.containers.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch(
                "module_data_fesco_api_adapter.cache.get_redis",
                return_value=mock_redis,
            ),
        ):
            result = await get_containers(datetime.date(2024, 6, 15), "dep1", "dest1")

        assert result == []


class TestSearchContainerIds:
    def test_finds_matching_containers(self):
        containers = [
            ContainerItem(id=1, size=20, type="DC", weight_from=0, weight_to=28000, name="20DC"),
            ContainerItem(id=2, size=20, type="DC", weight_from=28001, weight_to=50000, name="20DC"),
        ]

        assert search_container_ids(containers, weight=20000, container_type=20) == [1]
        assert search_container_ids(containers, weight=30000, container_type=20) == [2]

    def test_no_weight_to_returns_id(self):
        containers = [
            ContainerItem(id=1, size=20, type="DC", weight_from=0, weight_to=None, name="20DC"),
        ]
        assert search_container_ids(containers, weight=99999, container_type=20) == [1]

    def test_no_match_returns_empty(self):
        containers = [
            ContainerItem(id=1, size=20, type="DC", weight_from=0, weight_to=28000, name="20DC"),
        ]
        assert search_container_ids(containers, weight=99999, container_type=20) == []

    def test_wrong_size_returns_empty(self):
        containers = [
            ContainerItem(id=1, size=20, type="DC", weight_from=0, weight_to=28000, name="20DC"),
        ]
        assert search_container_ids(containers, weight=20000, container_type=40) == []


class TestGetDeparturePoints:
    @pytest.mark.asyncio
    async def test_success(self):
        raw_data = [
            {"id": "F1", "name": "Москва", "country": "Россия"},
            {"id": "F2", "name": "Владивосток", "country": "Россия"},
        ]
        mock_session = _mock_aiohttp_session({"data": raw_data})
        mock_redis = _mock_redis()

        with (
            patch(
                "module_data_fesco_api_adapter.api_client.points.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
        ):
            result = await get_departure_points_by_date(datetime.date(2024, 6, 15))

        assert len(result) == 2
        assert result[0]["id"] == "F1"

    @pytest.mark.asyncio
    async def test_http_error(self):
        mock_session = _mock_aiohttp_session({}, status_ok=False)
        mock_redis = _mock_redis()

        with (
            patch(
                "module_data_fesco_api_adapter.api_client.points.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
            pytest.raises(Exception, match="HTTP 500"),
        ):
            await get_departure_points_by_date(datetime.date(2024, 6, 15))


class TestGetDestinationPoints:
    @pytest.mark.asyncio
    async def test_success(self):
        raw_data = [
            {"id": "F3", "name": "Шанхай", "country": "Китай"},
        ]
        mock_session = _mock_aiohttp_session({"data": raw_data})
        mock_redis = _mock_redis()

        with (
            patch(
                "module_data_fesco_api_adapter.api_client.points.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
        ):
            result = await get_destination_points_by_date(
                datetime.date(2024, 6, 15), "F1"
            )

        assert len(result) == 1
        assert result[0]["id"] == "F3"

    @pytest.mark.asyncio
    async def test_http_error(self):
        mock_session = _mock_aiohttp_session({}, status_ok=False)
        mock_redis = _mock_redis()

        with (
            patch(
                "module_data_fesco_api_adapter.api_client.points.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
            pytest.raises(Exception, match="HTTP 500"),
        ):
            await get_destination_points_by_date(
                datetime.date(2024, 6, 15), "F1"
            )


class TestFindAllPaths:
    @pytest.mark.asyncio
    async def test_success(self):
        raw_route = {
            "DateFrom": "2024-06-01T00:00:00",
            "DateTo": "2024-06-30T00:00:00",
            "BeginCond": "",
            "FinishCond": "",
            "Containers": [
                {"ContainerCode": "C1", "ContainerNameEng": "(20'DC) 0-28t"}
            ],
            "Services": [],
            "Segments": [
                {
                    "SegmentUID": "s1",
                    "SegmentType": 2,
                    "BeginCountryName": "CN",
                    "BeginLocName": "Shanghai",
                    "FinishCountryName": "RU",
                    "FinishLocName": "Vladivostok",
                    "Containers": [{"Price": 2000.0, "Currency": "USD"}],
                }
            ],
        }
        mock_session = _mock_aiohttp_session({"data": [raw_route]})

        mock_redis = _mock_redis()
        with (
            patch(
                "module_data_fesco_api_adapter.api_client.routes.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
        ):
            result = await find_all_paths(
                datetime.date(2024, 6, 15),
                "dep1",
                "dest1",
                ["wte1"],
            )

        result_list = list(result)
        assert len(result_list) == 1
        assert result_list[0].segments[0].type == "sea"

    @pytest.mark.asyncio
    async def test_multiple_wte_ids(self):
        raw_route = {
            "DateFrom": "2024-06-01T00:00:00",
            "DateTo": "2024-06-30T00:00:00",
            "BeginCond": "",
            "FinishCond": "",
            "Containers": [
                {"ContainerCode": "C1", "ContainerNameEng": "(20'DC) 0-28t"}
            ],
            "Services": [],
            "Segments": [
                {
                    "SegmentUID": "s1",
                    "SegmentType": 1,
                    "BeginCountryName": "RU",
                    "BeginLocName": "A",
                    "FinishCountryName": "RU",
                    "FinishLocName": "B",
                    "Containers": [{"Price": 100.0, "Currency": "USD"}],
                }
            ],
        }
        mock_session = _mock_aiohttp_session({"data": [raw_route]})

        mock_redis = _mock_redis()
        with (
            patch(
                "module_data_fesco_api_adapter.api_client.routes.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
        ):
            result = await find_all_paths(
                datetime.date(2024, 6, 15),
                "dep1",
                "dest1",
                ["wte1", "wte2"],
            )

        result_list = list(result)
        assert len(result_list) == 2

    @pytest.mark.asyncio
    async def test_partial_failure_returns_successful_only(self):
        raw_route = {
            "DateFrom": "2024-06-01T00:00:00",
            "DateTo": "2024-06-30T00:00:00",
            "BeginCond": "",
            "FinishCond": "",
            "Containers": [
                {"ContainerCode": "C1", "ContainerNameEng": "(20'DC) 0-28t"}
            ],
            "Services": [],
            "Segments": [
                {
                    "SegmentUID": "s1",
                    "SegmentType": 1,
                    "BeginCountryName": "RU",
                    "BeginLocName": "A",
                    "FinishCountryName": "RU",
                    "FinishLocName": "B",
                    "Containers": [{"Price": 100.0, "Currency": "USD"}],
                }
            ],
        }
        mock_resp_ok = AsyncMock()
        mock_resp_ok.json = AsyncMock(return_value={"data": [raw_route]})
        mock_resp_ok.raise_for_status = MagicMock()

        mock_resp_fail = AsyncMock()
        mock_resp_fail.raise_for_status = MagicMock(side_effect=Exception("HTTP 500"))

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=[mock_resp_ok, mock_resp_fail])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_redis = _mock_redis()
        with (
            patch(
                "module_data_fesco_api_adapter.api_client.routes.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
        ):
            result = await find_all_paths(
                datetime.date(2024, 6, 15),
                "dep1",
                "dest1",
                ["wte1", "wte2"],
            )

        result_list = list(result)
        assert len(result_list) == 1

    @pytest.mark.asyncio
    async def test_empty_response(self):
        mock_session = _mock_aiohttp_session({"data": []})

        mock_redis = _mock_redis()
        with (
            patch(
                "module_data_fesco_api_adapter.api_client.routes.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
        ):
            result = await find_all_paths(
                datetime.date(2024, 6, 15),
                "dep1",
                "dest1",
                ["wte1"],
            )

        result_list = list(result)
        assert len(result_list) == 0

    @pytest.mark.asyncio
    async def test_all_failures_return_empty(self):
        mock_resp_fail = AsyncMock()
        mock_resp_fail.raise_for_status = MagicMock(side_effect=Exception("HTTP 500"))

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_resp_fail)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_redis = _mock_redis()
        with (
            patch(
                "module_data_fesco_api_adapter.api_client.routes.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
        ):
            result = await find_all_paths(
                datetime.date(2024, 6, 15),
                "dep1",
                "dest1",
                ["wte1"],
            )

        result_list = list(result)
        assert len(result_list) == 0

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        cached_route = {
            "segments": [
                {
                    "id": "s1",
                    "company": "FESCO",
                    "type": "sea",
                    "effectiveFrom": "2024-06-01T00:00:00",
                    "effectiveTo": "2024-06-30T00:00:00",
                    "startPointCountry": "CN",
                    "startPointName": "Shanghai",
                    "endPointCountry": "RU",
                    "endPointName": "Vladivostok",
                    "prices": [
                        {
                            "container": {
                                "id": "C1", "type": "DC", "size": 20,
                                "weight_from": 0, "weight_to": 28, "name": "20'DC 0-28t",
                            },
                            "value": 2000.0,
                            "currency": "USD",
                            "conversation_percents": 0.0,
                        }
                    ],
                }
            ],
            "drop": None,
            "may_be_invalid": False,
            "services": [],
        }
        mock_redis = _mock_redis(get_return=json.dumps([cached_route]))

        with patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis):
            result = await find_all_paths(
                datetime.date(2024, 6, 15), "dep1", "dest1", ["wte1"]
            )

        result_list = list(result)
        assert len(result_list) == 1
        assert result_list[0].segments[0].type == "sea"
        assert result_list[0].segments[0].company == "FESCO"

    @pytest.mark.asyncio
    async def test_cache_hit_corrupt(self):
        mock_redis = _mock_redis(get_return="not-valid-route-json")

        mock_session = _mock_aiohttp_session({"data": []})
        with (
            patch(
                "module_data_fesco_api_adapter.api_client.routes.aiohttp.ClientSession",
                return_value=mock_session,
            ),
            patch("module_data_fesco_api_adapter.cache.get_redis", return_value=mock_redis),
        ):
            result = await find_all_paths(
                datetime.date(2024, 6, 15), "dep1", "dest1", ["wte1"]
            )

        result_list = list(result)
        assert len(result_list) == 0
