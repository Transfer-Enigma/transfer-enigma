import pandas as pd
from backend_admin.service.routes_loading.loading import sync_validated, synchronize
from backend_admin.service.routes_loading.sync_errors import SyncErrorCode
from backend_admin.service.routes_loading.unit_of_work import UnitOfWork
from backend_admin.service.routes_loading.validation import load_reference_snapshot, validate_frames
from module_shared.schemas.company import CompanyModel
from module_shared.schemas.drop import DropModel
from module_shared.schemas.point import PointModel
from module_shared.schemas.route import PriceModel, RouteModel, RouteType, ServicePriceModel
from module_shared.schemas.service import ServiceModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .fixtures.frames import (
    clean_dropp_row,
    clean_sea_row,
    make_fc,
    make_frame,
    make_points_frame,
    make_services_frame,
    make_snapshot,
)


def _rail_row(fc, **overrides):
    row = clean_sea_row(
        fc,
        **{
            fc.effective_from: "2026-02-01",
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


TABLE_MODELS = (
    CompanyModel, PointModel, ServiceModel, RouteModel,
    PriceModel, ServicePriceModel, DropModel,
)


async def _table_counts(session: AsyncSession) -> dict:
    counts = {}
    for model in TABLE_MODELS:
        counts[model.__tablename__] = (await session.execute(
            select(func.count()).select_from(model),
        )).scalar_one()
    return counts


async def _seed_reference(session: AsyncSession) -> None:
    session.add(CompanyModel(name="FESCO"))
    session.add(PointModel(city="Vladivostok", country="RU", RU_city="Владивосток", RU_country="РФ"))
    session.add(PointModel(city="Moscow", country="RU", RU_city="Москва", RU_country="РФ"))
    session.add(ServiceModel(name="Exp", internal_name="exp", description="d"))
    await session.flush()


class TestUnitOfWork:
    async def test_wraps_session_and_commits(self, sqlite_session: AsyncSession):
        uow = UnitOfWork(sqlite_session)
        assert uow.session is sqlite_session
        sqlite_session.add(CompanyModel(name="UOW"))
        await uow.commit()
        names = (await sqlite_session.execute(select(CompanyModel.name))).scalars().all()
        assert "UOW" in names


class TestSynchronize:
    async def test_clean_frames_insert_everything(self, sqlite_session: AsyncSession):
        fc = make_fc()
        outcome = await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)

        assert outcome.ok is True
        assert outcome.built_routes == 2
        assert outcome.report.checked_rows == 3
        assert {error.code for error in outcome.report.errors} <= {
            SyncErrorCode.COMPANY_NOT_FOUND, SyncErrorCode.POINT_NOT_FOUND,
        }

        counts = await _table_counts(sqlite_session)
        assert counts["routes"] == 2
        assert counts["prices"] == 6
        assert counts["drop"] == 2
        assert counts["companies"] == 1
        company_names = (await sqlite_session.execute(select(CompanyModel.name))).scalars().all()
        assert company_names == ["FESCO"]

    async def test_gate_aborts_without_any_write(self, sqlite_session: AsyncSession):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.company: "ghost"})])
        frames["rail"] = make_frame(fc, [_rail_row(fc, **{fc.company: "ghost"})])
        frames["dropp"] = make_frame(fc, [clean_dropp_row(fc, **{fc.company: "ghost"})])
        counts_before = await _table_counts(sqlite_session)

        outcome = await synchronize(sqlite_session, frames, fc, "doc", False)

        assert outcome.ok is False
        assert outcome.built_routes == 0
        assert outcome.report.errors != []
        assert await _table_counts(sqlite_session) == counts_before

    async def test_partial_load_skips_invalid_rows(self, sqlite_session: AsyncSession):
        await _seed_reference(sqlite_session)
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.container_transfer_terms: "XXX"})])

        outcome = await synchronize(sqlite_session, frames, fc, "doc", True)

        assert outcome.ok is True
        assert outcome.built_routes == 1
        codes = [error.code for error in outcome.report.errors]
        assert SyncErrorCode.BAD_ENUM_VALUE in codes

        counts = await _table_counts(sqlite_session)
        assert counts["routes"] == 1
        company_names = (await sqlite_session.execute(select(CompanyModel.name))).scalars().all()
        assert company_names == ["FESCO"]

    async def test_unknown_company_is_created_like_before(self, sqlite_session: AsyncSession):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.company: "ghost"})])

        outcome = await synchronize(sqlite_session, frames, fc, "doc", True)

        assert outcome.ok is True
        assert outcome.built_routes == 2
        assert SyncErrorCode.COMPANY_NOT_FOUND in [error.code for error in outcome.report.errors]
        company_names = (await sqlite_session.execute(select(CompanyModel.name))).scalars().all()
        assert sorted(company_names) == ["FESCO", "GHOST"]

    async def test_point_absent_from_sheet_is_skipped(self, sqlite_session: AsyncSession):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.end_point: "Atlantis"})])

        outcome = await synchronize(sqlite_session, frames, fc, "doc", True)

        assert outcome.ok is True
        assert outcome.built_routes == 1
        assert SyncErrorCode.POINT_NOT_FOUND in [error.code for error in outcome.report.errors]

    async def test_unknown_uid_row_inserts_in_permissive_mode(self, sqlite_session: AsyncSession):
        fc = make_fc()
        await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.company: "ghost"})])

        outcome = await synchronize(sqlite_session, frames, fc, "doc", True)

        assert outcome.ok is True
        assert SyncErrorCode.UID_NOT_IN_DB in [error.code for error in outcome.report.errors]
        company_names = (await sqlite_session.execute(select(CompanyModel.name))).scalars().all()
        assert "GHOST" in company_names

    async def test_second_run_is_idempotent(self, sqlite_session: AsyncSession):
        fc = make_fc()
        first = await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)
        assert first.ok is True

        second = await synchronize(sqlite_session, _clean_frames(fc), fc, "doc", True)

        assert second.ok is True
        counts = await _table_counts(sqlite_session)
        assert counts["routes"] == 2
        assert counts["prices"] == 6
        assert counts["drop"] == 2

    async def test_dropp_missing_cells_are_classified(self, sqlite_session: AsyncSession):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["dropp"] = make_frame(fc, [clean_dropp_row(fc, **{fc.company: None})])

        outcome = await synchronize(sqlite_session, frames, fc, "doc", False)

        assert outcome.ok is False
        codes = [warning.code for warning in outcome.report.warnings]
        assert SyncErrorCode.REQUIRED_CELL_EMPTY in codes
        assert SyncErrorCode.UNKNOWN not in codes

    async def test_points_nan_reports_row_numbers(self, sqlite_session: AsyncSession):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["points"] = pd.DataFrame([{"city": "X", "country": None}])

        outcome = await synchronize(sqlite_session, frames, fc, "doc", False)

        assert outcome.ok is False
        assert [error.code for error in outcome.report.errors] == [SyncErrorCode.POINTS_SHEET_NAN]
        assert outcome.report.errors[0].details == {"row_numbers": [2]}


class TestSyncValidated:
    async def test_sync_uses_validated_data_only(self, sqlite_session: AsyncSession):
        await _seed_reference(sqlite_session)
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.container_transfer_terms: "XXX"})])
        snapshot = await load_reference_snapshot(sqlite_session)
        validated = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, snapshot, document="doc",
        )
        assert ("SEA", 0) in validated.row_errors

        result = await sync_validated(UnitOfWork(sqlite_session), validated, fc)

        assert result.built_routes == 1
        assert result.skipped_rows == 1
        counts = await _table_counts(sqlite_session)
        assert counts["routes"] == 1

    async def test_validated_data_carries_frames(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        validated = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(), document="doc",
        )
        assert len(validated.routes_df) == 2
        assert len(validated.dropp_df) == 1
        assert validated.points_df is not None
        assert len(validated.points_df) >= 1
        assert validated.document == "doc"
        assert RouteType.SEA in set(validated.routes_df[fc.route_type])
