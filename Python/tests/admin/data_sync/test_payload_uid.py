import re
from datetime import date

from backend_admin.schemas.data_browser import SyncDocumentCreate
from backend_admin.service.crud_sync_documents import crud_sync_documents
from backend_admin.service.routes_loading.loading import synchronize
from backend_admin.service.routes_loading.uid import fingerprint_drop, fingerprint_route
from module_shared.schemas.company import CompanyModel
from module_shared.schemas.container import ContainerModel, ContainerType
from module_shared.schemas.drop import DropModel
from module_shared.schemas.point import PointModel
from module_shared.schemas.route import PriceModel, RouteModel, RouteType
from sqlalchemy import event, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from .fixtures.frames import (
    clean_dropp_row,
    clean_sea_row,
    make_fc,
    make_frame,
    make_points_frame,
    make_services_frame,
)


def _rail_row(fc, **overrides):
    row = clean_sea_row(
        fc,
        **{
            fc.rail_20dc24t: 100.0,
            fc.rail_20dc28t: 150.0,
            fc.rail_40hc: 200.0,
            fc.rail_20dc24t_currency: "USD",
            fc.rail_20dc28t_currency: "USD",
            fc.rail_40hc_currency: "USD",
        },
    )
    row.update(overrides)
    return row


def _clean_frames(fc):
    return {
        "sea": make_frame(fc, [clean_sea_row(fc)]),
        "rail": make_frame(fc, [_rail_row(fc)]),
        "truck": None,
        "dropp": make_frame(fc, [clean_dropp_row(fc)]),
        "services": make_services_frame(fc),
        "points": make_points_frame(),
    }


def _doc_payload(**overrides):
    payload = {"title": "Doc", "url": "https://docs.google.com/spreadsheets/d/abc"}
    payload.update(overrides)
    return SyncDocumentCreate(**payload)


async def _sea_price(session: AsyncSession, size: int, weight_from: float) -> float:
    price = (await session.execute(
        select(PriceModel)
        .join(PriceModel.route)
        .join(PriceModel.container)
        .where(
            RouteModel.type == RouteType.SEA,
            ContainerModel.size == size,
            ContainerModel.weight_from == weight_from,
        ),
    )).scalars().one()
    return price.value


async def _route_prices(session: AsyncSession, route_type: RouteType) -> dict:
    rows = (await session.execute(
        select(
            ContainerModel.size,
            ContainerModel.weight_from,
            ContainerModel.weight_to,
            PriceModel.value,
        )
        .join(PriceModel.container)
        .join(PriceModel.route)
        .where(RouteModel.type == route_type),
    )).all()
    return {(size, weight_from, weight_to): value for size, weight_from, weight_to, value in rows}


async def _drop_items(session: AsyncSession) -> list:
    return list((await session.execute(
        select(DropModel).options(
            joinedload(DropModel.start_point),
            joinedload(DropModel.end_point),
            joinedload(DropModel.company),
            joinedload(DropModel.container),
        ),
    )).scalars().all())


async def _routes_by_type(session: AsyncSession) -> dict:
    routes = (await session.execute(
        select(RouteModel).options(
            selectinload(RouteModel.prices),
            selectinload(RouteModel.services),
        ),
    )).scalars().all()
    return {route.type: route for route in routes}


class TestFingerprint:
    def test_drop_fingerprint_is_price_sensitive_without_db(self):
        company = CompanyModel(name="FESCO")
        start = PointModel(city="Vladivostok", country="RU")
        end = PointModel(city="Moscow", country="RU")
        container = ContainerModel(size=20, type=ContainerType.DC,
                                   weight_from=0, weight_to=24, name="20DC")

        def _drop(price):
            return DropModel(
                start_point=start, end_point=end, company=company, container=container,
                effective_from=date(2026, 1, 1), effective_to=date(2026, 12, 31),
                price=price, currency="USD",
            )

        assert fingerprint_drop(_drop(50.0)) != fingerprint_drop(_drop(70.0))
        assert fingerprint_drop(_drop(50.0)) == fingerprint_drop(_drop(50.0))

    async def test_hash_is_deterministic(self, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)
        routes = await _routes_by_type(sqlite_session)

        assert re.fullmatch(r"[0-9a-f]{64}", routes[RouteType.SEA].payload_hash)
        assert re.fullmatch(r"[0-9a-f]{64}", routes[RouteType.RAIL].payload_hash)
        assert routes[RouteType.SEA].payload_hash != routes[RouteType.RAIL].payload_hash
        assert fingerprint_route(routes[RouteType.SEA]) == routes[RouteType.SEA].payload_hash

    async def test_hash_changes_with_price(self, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)
        before = (await _routes_by_type(sqlite_session))[RouteType.SEA].payload_hash

        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.sea_20dc: 150.0})])
        await synchronize(sqlite_session, frames, fc, "doc", True)
        after = (await _routes_by_type(sqlite_session))[RouteType.SEA].payload_hash

        assert before != after

    async def test_drop_hash_changes_with_price(self, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)
        before_hashes = {item.payload_hash for item in await _drop_items(sqlite_session)}
        assert before_hashes != {None}

        frames = _clean_frames(fc)
        frames["dropp"] = make_frame(fc, [clean_dropp_row(fc, **{fc.drop20: 70.0})])
        await synchronize(sqlite_session, frames, fc, "doc", True)
        after = await _drop_items(sqlite_session)

        assert sorted(item.price for item in after) == [70.0, 70.0]
        after_hashes = {item.payload_hash for item in after}
        assert before_hashes != after_hashes
        assert fingerprint_drop(after[0]) == after[0].payload_hash


class TestUpsert:
    async def test_sea_and_rail_with_same_dates_coexist(self, sqlite_session: AsyncSession):
        fc = make_fc()
        outcome = await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)

        assert outcome.ok is True
        assert outcome.built_routes == 2
        routes = await _routes_by_type(sqlite_session)
        assert set(routes) == {RouteType.SEA, RouteType.RAIL}

    async def test_price_update_replaces_without_duplicates(self, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)
        assert await _sea_price(sqlite_session, 20, 0) == 100.0

        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.sea_20dc: 150.0})])
        outcome = await synchronize(sqlite_session, frames, fc, "doc", True)

        assert outcome.ok is True
        assert await _sea_price(sqlite_session, 20, 0) == 150.0
        assert await _route_prices(sqlite_session, RouteType.SEA) == {
            (20, 0, 24): 150.0,
            (20, 24, 28): 150.0,
            (40, 0, 28): 200.0,
        }
        routes_count = (await sqlite_session.execute(
            select(func.count()).select_from(RouteModel),
        )).scalar_one()
        prices_count = (await sqlite_session.execute(
            select(func.count()).select_from(PriceModel),
        )).scalar_one()
        assert routes_count == 2
        assert prices_count == 6

    async def test_mode_new_never_updates(self, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)

        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.sea_20dc: 999.0})])
        outcome = await synchronize(
            sqlite_session, frames, fc, "doc", True, update_existing=False,
        )

        assert outcome.ok is True
        assert await _sea_price(sqlite_session, 20, 0) == 100.0
        routes_count = (await sqlite_session.execute(
            select(func.count()).select_from(RouteModel),
        )).scalar_one()
        assert routes_count == 2

    async def test_drop_price_update(self, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)

        frames = _clean_frames(fc)
        frames["dropp"] = make_frame(fc, [clean_dropp_row(fc, **{fc.drop20: 70.0})])
        await synchronize(sqlite_session, frames, fc, "doc", True)

        items = (await sqlite_session.execute(select(DropModel))).scalars().all()
        assert len(items) == 2
        assert sorted(item.price for item in items) == [70.0, 70.0]


class TestSyncDocumentLink:
    async def test_document_id_recorded_and_updated(self, sqlite_session: AsyncSession):
        first = await crud_sync_documents.create(sqlite_session, _doc_payload(title="First"))
        second = await crud_sync_documents.create(sqlite_session, _doc_payload(title="Second"))
        fc = make_fc()

        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True, sync_document_id=first.id)
        routes = await _routes_by_type(sqlite_session)
        assert {route.sync_document_id for route in routes.values()} == {first.id}

        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True, sync_document_id=second.id)
        routes = await _routes_by_type(sqlite_session)
        assert {route.sync_document_id for route in routes.values()} == {second.id}


async def _price_ids(session: AsyncSession) -> list[int]:
    return sorted(
        (await session.execute(select(PriceModel.id))).scalars().all(),
    )


class TestUidRepeatSync:
    async def test_repeat_sync_preserves_price_ids(self, sqlite_db, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)
        before = await _price_ids(sqlite_session)
        assert len(before) == 6

        statements: list[str] = []

        def _count(conn, clauseelement, *args):
            statements.append(str(clauseelement))

        engine = sqlite_db._engine.sync_engine
        event.listen(engine, "before_cursor_execute", _count)
        try:
            outcome = await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)
        finally:
            event.remove(engine, "before_cursor_execute", _count)

        assert outcome.ok is True
        assert outcome.deleted_routes == 0
        assert outcome.deleted_dropp == 0
        assert await _price_ids(sqlite_session) == before
        updates = [s for s in statements if s.lstrip().upper().startswith("UPDATE")]
        assert updates == []


class TestUidPrune:
    async def test_missing_row_deleted_and_counted(self, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)

        frames = _clean_frames(fc)
        frames["rail"] = make_frame(fc, [_rail_row(fc, **{fc.company: "other-co"})])
        outcome = await synchronize(sqlite_session, frames, fc, "doc", True)

        assert outcome.ok is True
        assert outcome.deleted_routes == 1
        assert outcome.deleted_dropp == 0
        routes = await _routes_by_type(sqlite_session)
        assert set(routes) == {RouteType.SEA, RouteType.RAIL}
        assert routes[RouteType.RAIL].company.name == "OTHER-CO"

    async def test_invalid_but_present_row_kept(self, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)

        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.sea_20dc: None, fc.sea_40hc: None})])
        outcome = await synchronize(sqlite_session, frames, fc, "doc", True)

        assert outcome.ok is True
        assert outcome.deleted_routes == 0
        assert await _sea_price(sqlite_session, 20, 0) == 100.0
        routes_count = (await sqlite_session.execute(
            select(func.count()).select_from(RouteModel),
        )).scalar_one()
        assert routes_count == 2

    async def test_fatal_scope_skips_prune(self, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)

        frames = _clean_frames(fc)
        frames["points"] = make_points_frame(country=None)
        outcome = await synchronize(sqlite_session, frames, fc, "doc", True)

        assert outcome.deleted_routes == 0
        assert outcome.deleted_dropp == 0
        routes_count = (await sqlite_session.execute(
            select(func.count()).select_from(RouteModel),
        )).scalar_one()
        drop_count = (await sqlite_session.execute(
            select(func.count()).select_from(DropModel),
        )).scalar_one()
        assert routes_count == 2
        assert drop_count == 2

    async def test_mode_new_skips_prune(self, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)

        frames = _clean_frames(fc)
        frames["rail"] = make_frame(fc, [_rail_row(fc, **{fc.company: "other-co"})])
        outcome = await synchronize(
            sqlite_session, frames, fc, "doc", True, update_existing=False,
        )

        assert outcome.ok is True
        assert outcome.deleted_routes == 0
        routes_count = (await sqlite_session.execute(
            select(func.count()).select_from(RouteModel),
        )).scalar_one()
        assert routes_count == 3

    async def test_legacy_rows_without_hash_take_part(self, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)
        await sqlite_session.execute(update(RouteModel).values(payload_hash=None, sync_document_id=None))
        await sqlite_session.execute(update(DropModel).values(payload_hash=None, sync_document_id=None))

        frames = _clean_frames(fc)
        frames["rail"] = make_frame(fc, [_rail_row(fc, **{fc.company: "other-co"})])
        outcome = await synchronize(sqlite_session, frames, fc, "doc", True)

        assert outcome.deleted_routes == 1
        routes = await _routes_by_type(sqlite_session)
        assert set(routes) == {RouteType.SEA, RouteType.RAIL}
        assert all(route.payload_hash for route in routes.values())

    async def test_cross_document_overlap_updates_single_row(self, sqlite_session: AsyncSession):
        first = await crud_sync_documents.create(sqlite_session, _doc_payload(title="First"))
        second = await crud_sync_documents.create(sqlite_session, _doc_payload(title="Second"))
        fc = make_fc()

        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True, sync_document_id=first.id)
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True, sync_document_id=second.id)

        routes = await _routes_by_type(sqlite_session)
        assert set(routes) == {RouteType.SEA, RouteType.RAIL}
        assert {route.sync_document_id for route in routes.values()} == {second.id}
        routes_count = (await sqlite_session.execute(
            select(func.count()).select_from(RouteModel),
        )).scalar_one()
        assert routes_count == 2
