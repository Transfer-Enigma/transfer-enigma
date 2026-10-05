import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from starlette.requests import Request

import pytest
from backend_user.api.v2.route_collections import create as collections_create
from backend_user.api.v2.route_collections import get as collections_get
from backend_user.dependencies.auth_context import AuthContext
from backend_user.schemas.route_collections import CollectionItem, CreateCollectionRequest
from backend_user.services.route_collection import (
    create_collection,
    get_collection,
    resolve_collection,
)
from backend_user.services.route_link import RouteLinkNotFoundError
from module_shared.database import Database
from module_shared.models.route import RouteResult
from module_shared.schemas.container import ContainerType
from module_shared.schemas.route import RouteType
from module_shared.schemas.route_collection import RouteCollectionModel

from .data import (
    CompanyFactory,
    ContainerFactory,
    PointFactory,
    PriceFactory,
    RouteFactory,
    ServiceFactory,
    ServicePriceFactory,
)

LINK_DB = "backend_user.services.route_link.get_database"
COLLECTION_DB = "backend_user.services.route_collection.get_database"


def _demo_auth(uid: str) -> AuthContext:
    return AuthContext(is_demo=True, demo_uid=uid, sea_profit=10.0, rail_profit=5.0)


def _user_auth() -> AuthContext:
    return AuthContext()


def _request(demo_uid: str | None = None) -> Request:
    headers = []
    if demo_uid is not None:
        headers.append((b"x-demo-user-uid", demo_uid.encode()))
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


async def _seed_pair(session):
    company = CompanyFactory(name="CollectionCo")
    point_a = PointFactory(city="CA", RU_city="КА")
    point_b = PointFactory(city="CB", RU_city="КБ")
    point_c = PointFactory(city="CC", RU_city="КВ")
    container = ContainerFactory(size=20, weight_from=0, weight_to=28000, name="20DC", type=ContainerType.DC)
    session.add_all([company, point_a, point_b, point_c, container])
    await session.flush()

    seg1 = RouteFactory(
        company_id=company.id,
        start_point_id=point_a.id,
        end_point_id=point_b.id,
        type=RouteType.RAIL,
        effective_to=datetime.datetime(2030, 1, 1),
    )
    seg2 = RouteFactory(
        company_id=company.id,
        start_point_id=point_b.id,
        end_point_id=point_c.id,
        type=RouteType.RAIL,
        effective_to=datetime.datetime(2030, 1, 1),
    )
    session.add_all([seg1, seg2])
    await session.flush()
    session.add_all([
        PriceFactory(route_id=seg1.id, container_id=container.id),
        PriceFactory(route_id=seg2.id, container_id=container.id),
    ])

    svc1 = ServiceFactory(name="SVC1", internal_name="svc1", mandatory=False, default=False)
    svc2 = ServiceFactory(name="SVC2", internal_name="svc2", mandatory=False, default=True)
    session.add_all([svc1, svc2])
    await session.flush()
    sp1 = ServicePriceFactory(route_id=seg1.id, service_id=svc1.id, currency="USD", price=10.0)
    sp2 = ServicePriceFactory(route_id=seg2.id, service_id=svc2.id, currency="USD", price=20.0)
    session.add_all([sp1, sp2])
    await session.commit()
    return seg1, seg2, sp1, sp2


def _db_patches(sqlite_db: Database):
    return (
        patch(LINK_DB, return_value=sqlite_db),
        patch(COLLECTION_DB, return_value=sqlite_db),
    )


@pytest.mark.asyncio
async def test_create_collection_ok(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        seg1, seg2, sp1, _sp2 = await _seed_pair(session)

    patch_link, patch_collection = _db_patches(sqlite_db)
    with patch_link, patch_collection:
        model = await create_collection(
            [
                CollectionItem(segments=[seg1.id, seg2.id], services=[sp1.id]),
                CollectionItem(segments=[seg1.id], services=[]),
            ],
            demo_uid="demo-1",
        )

    assert len(model.uid) == 32
    assert model.demo_uid == "demo-1"
    assert model.items == [
        {"segments": [seg1.id, seg2.id], "services": [sp1.id]},
        {"segments": [seg1.id], "services": []},
    ]


@pytest.mark.asyncio
async def test_create_collection_no_demo(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        seg1, _seg2, _sp1, _sp2 = await _seed_pair(session)

    patch_link, patch_collection = _db_patches(sqlite_db)
    with patch_link, patch_collection:
        model = await create_collection([CollectionItem(segments=[seg1.id], services=[])], demo_uid=None)

    assert model.demo_uid is None


@pytest.mark.asyncio
async def test_create_collection_invalid(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        seg1, _seg2, _sp1, _sp2 = await _seed_pair(session)

    patch_link, patch_collection = _db_patches(sqlite_db)
    with patch_link, patch_collection, pytest.raises(RouteLinkNotFoundError):
        await create_collection([CollectionItem(segments=[seg1.id, 999999], services=[])], demo_uid=None)


@pytest.mark.asyncio
async def test_get_collection_missing(sqlite_db: Database):
    with patch(COLLECTION_DB, return_value=sqlite_db):
        assert await get_collection("no-such-uid") is None


@pytest.mark.asyncio
async def test_resolve_collection_ok(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        seg1, seg2, sp1, sp2 = await _seed_pair(session)

    patch_link, patch_collection = _db_patches(sqlite_db)
    with patch_link, patch_collection:
        model = await create_collection(
            [CollectionItem(segments=[seg1.id, seg2.id], services=[sp1.id, sp2.id])],
            demo_uid=None,
        )
        routes = await resolve_collection(model)

    assert len(routes) == 1
    assert [s.id for s in routes[0].segments] == [seg1.id, seg2.id]
    assert all(s.checked for s in routes[0].services)


@pytest.mark.asyncio
async def test_resolve_collection_broken(sqlite_db: Database):
    async with sqlite_db.session_context() as session:
        session.add(RouteCollectionModel(
            uid="broken-collection",
            demo_uid=None,
            items=[{"segments": [424242], "services": []}],
        ))
        await session.commit()

    with patch(COLLECTION_DB, return_value=sqlite_db), patch(LINK_DB, return_value=sqlite_db):
        model = await get_collection("broken-collection")
    assert model is not None
    with patch(LINK_DB, return_value=sqlite_db), pytest.raises(RouteLinkNotFoundError):
        await resolve_collection(model)


def _collection_stub(uid: str = "collection-uid", demo_uid: str | None = None):
    return SimpleNamespace(uid=uid, demo_uid=demo_uid, items=[])


def _route_stub() -> RouteResult:
    from module_shared.models.route import RouteSegment

    segment = RouteSegment(
        id=1,
        company="Co",
        type="RAIL",
        effectiveFrom="2024-01-01",
        effectiveTo="2030-01-01",
        startPointCountry="C",
        startPointName="A",
        endPointCountry="C",
        endPointName="B",
    )
    return RouteResult(segments=[segment], services=[])


def _patch_collection_get(stub, routes=None):
    service = collections_get.route_collection
    resolve = AsyncMock(return_value=routes if routes is not None else [_route_stub()])
    return (
        patch.object(service, "get_collection", new=AsyncMock(return_value=stub)),
        patch.object(service, "resolve_collection", new=resolve),
        patch.object(collections_get, "_apply_demo_transforms", new=AsyncMock()),
    )


@pytest.mark.asyncio
async def test_get_endpoint_plain_user_ok():
    patch_get, patch_resolve, patch_demo = _patch_collection_get(_collection_stub())
    with patch_get, patch_resolve, patch_demo:
        response = await collections_get.get_collection_endpoint(uid="x", request=_request(), auth=_user_auth())

    assert response["uid"] == "collection-uid"
    assert len(response["routes"]) == 1


@pytest.mark.asyncio
async def test_get_endpoint_plain_via_demo_forbidden():
    patch_get, _patch_resolve, patch_demo = _patch_collection_get(_collection_stub())
    with patch_get, _patch_resolve, patch_demo, pytest.raises(HTTPException) as exc:
        await collections_get.get_collection_endpoint(
            uid="x", request=_request("demo-1"), auth=_demo_auth("demo-1")
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_endpoint_demo_own_ok():
    stub = _collection_stub(demo_uid="demo-1")
    patch_get, patch_resolve, patch_demo = _patch_collection_get(stub)
    with patch_get, patch_resolve, patch_demo:
        response = await collections_get.get_collection_endpoint(
            uid="x", request=_request("demo-1"), auth=_demo_auth("demo-1")
        )

    assert len(response["routes"]) == 1


@pytest.mark.asyncio
async def test_get_endpoint_demo_other_forbidden():
    stub = _collection_stub(demo_uid="demo-1")
    patch_get, _patch_resolve, patch_demo = _patch_collection_get(stub)
    with patch_get, _patch_resolve, patch_demo, pytest.raises(HTTPException) as exc:
        await collections_get.get_collection_endpoint(
            uid="x", request=_request("demo-2"), auth=_demo_auth("demo-2")
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_endpoint_demo_bound_user_ok():
    stub = _collection_stub(demo_uid="demo-1")
    patch_get, patch_resolve, patch_demo = _patch_collection_get(stub)
    with patch_get, patch_resolve, patch_demo:
        response = await collections_get.get_collection_endpoint(uid="x", request=_request(), auth=_user_auth())

    assert len(response["routes"]) == 1


@pytest.mark.asyncio
async def test_get_endpoint_unknown_uid():
    service = collections_get.route_collection
    patch_get = patch.object(service, "get_collection", new=AsyncMock(return_value=None))
    with patch_get, pytest.raises(HTTPException) as exc:
        await collections_get.get_collection_endpoint(uid="x", request=_request(), auth=_user_auth())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_endpoint_broken_item():
    service = collections_get.route_collection
    patch_get = patch.object(service, "get_collection", new=AsyncMock(return_value=_collection_stub()))
    patch_broken = patch.object(
        service, "resolve_collection", new=AsyncMock(side_effect=RouteLinkNotFoundError("gone"))
    )
    with patch_get, patch_broken, pytest.raises(HTTPException) as exc:
        await collections_get.get_collection_endpoint(uid="x", request=_request(), auth=_user_auth())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_endpoint_binds_demo():
    created = SimpleNamespace(uid="new-uid")
    service = collections_create.route_collection
    patch_create = patch.object(service, "create_collection", new=AsyncMock(return_value=created))
    with patch_create as mock_create:
        response = await collections_create.create_collection_endpoint(
            request=CreateCollectionRequest(items=[{"segments": [1], "services": []}]),
            auth=_demo_auth("demo-9"),
        )

    assert response == {"uid": "new-uid"}
    assert mock_create.await_args.args[1] == "demo-9"


@pytest.mark.asyncio
async def test_create_endpoint_invalid_item():
    service = collections_create.route_collection
    patch_create = patch.object(
        service, "create_collection", new=AsyncMock(side_effect=RouteLinkNotFoundError("bad"))
    )
    with patch_create, pytest.raises(HTTPException) as exc:
        await collections_create.create_collection_endpoint(
            request=CreateCollectionRequest(items=[{"segments": [1], "services": []}]),
            auth=_user_auth(),
        )

    assert exc.value.status_code == 422
