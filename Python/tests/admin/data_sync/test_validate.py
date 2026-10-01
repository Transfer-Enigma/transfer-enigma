import pandas as pd
from backend_admin.service.routes_loading.rules import (
    RULES,
    RowContext,
    row_natural_uid,
    rule,
    run_row_rules,
)
from backend_admin.service.routes_loading.sync_errors import SyncErrorCode
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


def _ctx(fc, row_dict, snapshot, scope="route", route_type=RouteType.SEA,
         sheet="МОРЕ", row_number=3, document=None):
    return RowContext(
        row=pd.Series(row_dict),
        fields_config=fc,
        snapshot=snapshot,
        sheet=sheet,
        row_number=row_number,
        route_type=route_type,
        scope=scope,
        document=document,
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


class TestRowRules:
    def test_required_route_cells(self):
        fc = make_fc()
        row = clean_sea_row(fc, **{fc.company: float("nan")})
        findings = run_row_rules(_ctx(fc, row, make_snapshot()))
        assert len(findings) == 1
        assert findings[0].code == SyncErrorCode.REQUIRED_CELL_EMPTY
        assert findings[0].severity == "warning"
        assert fc.company in (findings[0].cell or "")

    def test_required_dropp_cells(self):
        fc = make_fc()
        row = clean_dropp_row(fc, **{fc.end_point: float("nan")})
        ctx = _ctx(fc, row, make_snapshot(), scope="dropp", route_type=None, sheet="ДРОПП")
        findings = run_row_rules(ctx)
        assert [finding.code for finding in findings] == [SyncErrorCode.REQUIRED_CELL_EMPTY]

    def test_full_row_has_no_required_findings(self):
        fc = make_fc()
        findings = run_row_rules(_ctx(fc, clean_sea_row(fc), make_snapshot()))
        assert findings == []

    def test_bad_effective_date(self):
        fc = make_fc()
        row = clean_sea_row(fc, **{fc.effective_to: float("nan")})
        findings = run_row_rules(_ctx(fc, row, make_snapshot()))
        codes = [finding.code for finding in findings]
        assert SyncErrorCode.BAD_DATE_FORMAT in codes
        warning = next(finding for finding in findings if finding.code == SyncErrorCode.BAD_DATE_FORMAT)
        assert warning.severity == "warning"
        assert warning.cell == fc.effective_to

    def test_bad_enum_value(self):
        fc = make_fc()
        row = clean_sea_row(fc, **{fc.container_transfer_terms: "XXX"})
        findings = run_row_rules(_ctx(fc, row, make_snapshot()))
        assert [finding.code for finding in findings] == [SyncErrorCode.BAD_ENUM_VALUE]
        assert findings[0].cell == fc.container_transfer_terms

    def test_bad_route_type(self):
        fc = make_fc()
        findings = run_row_rules(_ctx(fc, clean_sea_row(fc), make_snapshot(), route_type="AVIA"))
        assert [finding.code for finding in findings] == [SyncErrorCode.BAD_ENUM_VALUE]

    def test_unknown_company(self):
        fc = make_fc()
        row = clean_sea_row(fc, **{fc.company: "no-such-co"})
        findings = run_row_rules(_ctx(fc, row, make_snapshot()))
        assert [finding.code for finding in findings] == [SyncErrorCode.COMPANY_NOT_FOUND]

    def test_known_company_case_insensitive(self):
        fc = make_fc()
        findings = run_row_rules(_ctx(fc, clean_sea_row(fc), make_snapshot()))
        assert SyncErrorCode.COMPANY_NOT_FOUND not in [finding.code for finding in findings]

    def test_unknown_point(self):
        fc = make_fc()
        row = clean_sea_row(fc, **{fc.end_point: "Atlantis"})
        findings = run_row_rules(_ctx(fc, row, make_snapshot()))
        assert [finding.code for finding in findings] == [SyncErrorCode.POINT_NOT_FOUND]
        assert findings[0].cell == fc.end_point

    def test_missing_point_cell_skipped(self):
        fc = make_fc()
        row = clean_sea_row(fc, **{fc.end_point: float("nan")})
        findings = run_row_rules(_ctx(fc, row, make_snapshot()))
        assert SyncErrorCode.POINT_NOT_FOUND not in [finding.code for finding in findings]

    def test_route_without_price(self):
        fc = make_fc()
        row = clean_sea_row(fc, **{fc.sea_20dc: float("nan"), fc.sea_40hc: float("nan")})
        findings = run_row_rules(_ctx(fc, row, make_snapshot()))
        assert [finding.code for finding in findings] == [SyncErrorCode.NO_PRICE]

    def test_invalid_dropp_row(self):
        fc = make_fc()
        row = clean_dropp_row(fc, **{fc.company: ""})
        ctx = _ctx(fc, row, make_snapshot(), scope="dropp", route_type=None, sheet="ДРОПП")
        findings = run_row_rules(ctx)
        assert [finding.code for finding in findings] == [SyncErrorCode.DROPP_ROW_INVALID]

    def test_scope_filtering(self):
        fc = make_fc()
        route_findings = run_row_rules(_ctx(fc, clean_dropp_row(fc), make_snapshot(), scope="route"))
        assert SyncErrorCode.DROPP_ROW_INVALID not in [finding.code for finding in route_findings]
        dropp_ctx = _ctx(
            fc, clean_sea_row(fc), make_snapshot(), scope="dropp", route_type=None, sheet="ДРОПП",
        )
        dropp_findings = run_row_rules(dropp_ctx)
        assert SyncErrorCode.NO_PRICE not in [finding.code for finding in dropp_findings]
        assert SyncErrorCode.BAD_ENUM_VALUE not in [finding.code for finding in dropp_findings]

    def test_registry_is_extensible(self):
        count_before = len(RULES)
        assert count_before > 0
        assert {rule.code for rule in RULES} >= {
            SyncErrorCode.REQUIRED_CELL_EMPTY,
            SyncErrorCode.BAD_ENUM_VALUE,
            SyncErrorCode.COMPANY_NOT_FOUND,
            SyncErrorCode.POINT_NOT_FOUND,
            SyncErrorCode.NO_PRICE,
            SyncErrorCode.DROPP_ROW_INVALID,
        }

        @rule(SyncErrorCode.UNKNOWN, scope="route")
        def _custom(_ctx):
            return None

        try:
            assert len(RULES) == count_before + 1
        finally:
            RULES.remove(RULES[-1])


class TestValidateFrames:
    def test_clean_frames_have_no_findings(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(), document="doc",
        )
        assert report.errors == []
        assert report.warnings == []
        assert report.checked_rows == 3

    def test_broken_row_collects_all_codes_without_duplicates(self):
        fc = make_fc()
        broken = clean_sea_row(
            fc,
            **{
                fc.company: "unknown-co",
                fc.end_point: "Atlantis",
                fc.sea_20dc: float("nan"),
                fc.sea_40hc: float("nan"),
                fc.container_transfer_terms: "XXX",
            },
        )
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [broken])
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(), document="doc",
        )
        codes = sorted(finding.code for finding in report.errors)
        assert codes == [
            SyncErrorCode.BAD_ENUM_VALUE,
            SyncErrorCode.COMPANY_NOT_FOUND,
            SyncErrorCode.NO_PRICE,
            SyncErrorCode.POINT_NOT_FOUND,
        ]
        assert all(finding.document == "doc" for finding in report.errors)
        assert all(finding.row == 2 for finding in report.errors)
        assert SyncErrorCode.UNKNOWN not in codes

    def test_missing_cells_warn_but_do_not_fail(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.company: None})])
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(),
        )
        assert report.errors == []
        assert [warning.code for warning in report.warnings] == [SyncErrorCode.REQUIRED_CELL_EMPTY]
        assert report.warnings[0].details["rows_list"][0]["row_number"] == 2
        assert report.checked_rows == 2

    def test_unparseable_date_warns(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.effective_to: "not-a-date"})])
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(),
        )
        assert report.errors == []
        assert [warning.code for warning in report.warnings] == [SyncErrorCode.BAD_DATE_FORMAT]

    def test_points_nan_is_fatal(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["points"] = pd.DataFrame([{"city": "X", "country": float("nan")}])
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(), points_sheet="Точки",
        )
        assert [error.code for error in report.errors] == [SyncErrorCode.POINTS_SHEET_NAN]
        assert report.errors[0].sheet == "Точки"
        assert report.checked_rows == 0

    def test_terminal_points_resolve_without_db_rows(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["points"] = pd.DataFrame([
            {"city": "Vladivostok", "country": "RU", "RU_city": "Владивосток", "RU_country": "РФ"},
            {"city": "Novorossiysk", "country": "RU", "RU_city": "Новороссийск", "RU_country": "РФ"},
        ])
        frames["sea"] = make_frame(fc, [
            clean_sea_row(fc, **{fc.end_point: "Novorossiysk", fc.terminal: "T1"}),
        ])
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(),
        )
        assert SyncErrorCode.POINT_NOT_FOUND not in [error.code for error in report.errors]

    def test_trial_build_backstop_never_raises(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.exp: "not-a-number"})])
        snapshot = make_snapshot(services=("exp",))
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, snapshot,
        )
        assert len(report.errors) == 1
        assert report.errors[0].code == SyncErrorCode.UNKNOWN

    def test_report_serializes(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(),
        )
        assert report.to_dict() == {"errors": [], "warnings": [], "checked_rows": 3}


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


class TestValidateDryRun:
    async def test_snapshot_loads_reference_data(self, sqlite_session: AsyncSession):
        sqlite_session.add(CompanyModel(name="FESCO"))
        sqlite_session.add(PointModel(city="Vladivostok", country="RU",
                                      RU_city="Владивосток", RU_country="РФ"))
        sqlite_session.add(ServiceModel(name="Exp", internal_name="exp", description="d"))
        await sqlite_session.flush()

        snapshot = await load_reference_snapshot(sqlite_session)

        assert snapshot.companies == frozenset({"FESCO"})
        assert snapshot.point_keys == frozenset({"vladivostok", "владивосток"})
        assert snapshot.services == frozenset({"exp"})

    async def test_validate_writes_nothing(self, sqlite_session: AsyncSession):
        sqlite_session.add(CompanyModel(name="FESCO"))
        sqlite_session.add(PointModel(city="Vladivostok", country="RU",
                                      RU_city="Владивосток", RU_country="РФ"))
        sqlite_session.add(PointModel(city="Moscow", country="RU",
                                      RU_city="Москва", RU_country="РФ"))
        sqlite_session.add(ServiceModel(name="Exp", internal_name="exp", description="d"))
        await sqlite_session.flush()

        counts_before = await _table_counts(sqlite_session)

        fc = make_fc()
        frames = _clean_frames(fc)
        snapshot = await load_reference_snapshot(sqlite_session)
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, snapshot,
        )

        assert report.errors == []
        assert report.checked_rows == 3
        assert await _table_counts(sqlite_session) == counts_before

    async def test_broken_frames_still_write_nothing(self, sqlite_session: AsyncSession):
        sqlite_session.add(CompanyModel(name="FESCO"))
        sqlite_session.add(PointModel(city="Vladivostok", country="RU",
                                      RU_city="Владивосток", RU_country="РФ"))
        sqlite_session.add(PointModel(city="Moscow", country="RU",
                                      RU_city="Москва", RU_country="РФ"))
        await sqlite_session.flush()

        counts_before = await _table_counts(sqlite_session)

        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.company: "ghost"})])
        snapshot = await load_reference_snapshot(sqlite_session)
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, snapshot,
        )

        assert [error.code for error in report.errors] == [SyncErrorCode.COMPANY_NOT_FOUND]
        assert await _table_counts(sqlite_session) == counts_before


class TestDuplicateRows:
    def test_exact_duplicate_flags_second_row(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc), clean_sea_row(fc)])
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(),
        )
        duplicates = [finding for finding in report.errors
                      if finding.code == SyncErrorCode.DUPLICATE_ROW]
        assert len(duplicates) == 1
        assert duplicates[0].row == 3
        assert duplicates[0].sheet == "МОРЕ"

    def test_normalized_duplicate_is_caught(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [
            clean_sea_row(fc, **{fc.company: "fesco"}),
            clean_sea_row(fc, **{fc.company: "FESCO "}),
        ])
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(),
        )
        assert [finding.code for finding in report.errors] == [SyncErrorCode.DUPLICATE_ROW]

    def test_triple_duplicate_flags_two_rows(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc)] * 3)
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(),
        )
        rows = sorted(
            finding.row for finding in report.errors
            if finding.code == SyncErrorCode.DUPLICATE_ROW
        )
        assert rows == [3, 4]

    def test_same_content_different_type_is_not_duplicate(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(),
        )
        assert SyncErrorCode.DUPLICATE_ROW not in [finding.code for finding in report.errors]

    def test_different_price_is_not_duplicate(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        frames["sea"] = make_frame(fc, [
            clean_sea_row(fc, **{fc.sea_20dc: 100.0}),
            clean_sea_row(fc, **{fc.sea_20dc: 150.0}),
        ])
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(),
        )
        assert SyncErrorCode.DUPLICATE_ROW not in [finding.code for finding in report.errors]


class TestUidKnownInDb:
    def test_unknown_uid_flagged(self):
        fc = make_fc()
        ctx = _ctx(fc, clean_sea_row(fc), make_snapshot(existing_row_uids={"other"}))
        findings = run_row_rules(ctx)
        codes = [finding.code for finding in findings]
        assert SyncErrorCode.UID_NOT_IN_DB in codes
        uid_finding = next(finding for finding in findings if finding.code == SyncErrorCode.UID_NOT_IN_DB)
        assert row_natural_uid(ctx) in uid_finding.message

    def test_known_uid_silent(self):
        fc = make_fc()
        probe = _ctx(fc, clean_sea_row(fc), make_snapshot())
        snapshot = make_snapshot(existing_row_uids={row_natural_uid(probe)})
        findings = run_row_rules(_ctx(fc, clean_sea_row(fc), snapshot))
        assert SyncErrorCode.UID_NOT_IN_DB not in [finding.code for finding in findings]

    def test_empty_uid_set_silent(self):
        fc = make_fc()
        findings = run_row_rules(_ctx(fc, clean_sea_row(fc), make_snapshot()))
        assert SyncErrorCode.UID_NOT_IN_DB not in [finding.code for finding in findings]

    def test_frames_level_unknown_uids(self):
        fc = make_fc()
        frames = _clean_frames(fc)
        report = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(existing_row_uids={"other"}),
        )
        uid_errors = [finding for finding in report.errors
                      if finding.code == SyncErrorCode.UID_NOT_IN_DB]
        assert len(uid_errors) == 3
        assert {finding.sheet for finding in uid_errors} == {"МОРЕ", "ЖД", "ДРОПП"}
