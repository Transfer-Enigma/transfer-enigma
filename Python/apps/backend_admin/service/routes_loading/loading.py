from dataclasses import dataclass, field

from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from backend_admin.service.routes_loading.error_reporting import parse_error, to_sync_error
from backend_admin.service.routes_loading.errors import LoadingErrorException
from backend_admin.service.routes_loading.sync_errors import SyncError, SyncErrorCode, make_error
from backend_admin.service.routes_loading.unit_of_work import UnitOfWork
from backend_admin.service.routes_loading.uploader import (
    create_dropp,
    create_route,
    load_companies,
    load_containers,
    load_dropp,
    load_points,
    load_routes,
    load_services,
)
from backend_admin.service.routes_loading.validation import (
    REFERENCE_CONTAINERS,
    ValidatedData,
    ValidationReport,
    load_reference_snapshot,
    validate_frames,
)
from module_shared.schemas.route import RouteType
from pandas import DataFrame
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class SyncResult:
    built_routes: int = 0
    built_dropp_groups: int = 0
    skipped_rows: int = 0
    extra_errors: list[SyncError] = field(default_factory=list)


@dataclass
class SyncOutcome:
    ok: bool
    built_routes: int
    report: ValidationReport


CREATABLE_CODES = frozenset({
    SyncErrorCode.COMPANY_NOT_FOUND,
    SyncErrorCode.POINT_NOT_FOUND,
    # Unknown rows are flagged for review but remain insertable:
    # in permissive mode they are loaded as new rows.
    SyncErrorCode.UID_NOT_IN_DB,
})


def _unexpected_sync_error(document: str | None, sheet: str, row: int, exc: Exception) -> SyncError:
    return make_error(
        SyncErrorCode.UNKNOWN,
        document=document,
        sheet=sheet,
        row=row,
        type=type(exc).__name__,
        detail=str(exc),
    )


def _mapped_sync_error(document: str | None, route_type, orig_idx: int, exc: Exception) -> SyncError:
    if isinstance(exc, (LoadingErrorException, ValueError, KeyError, AttributeError)):
        return to_sync_error(parse_error(exc, orig_idx, route_type, document=document))
    return _unexpected_sync_error(document, str(route_type), orig_idx + 2, exc)


def _is_buildable(findings: list[SyncError]) -> bool:
    return all(finding.code in CREATABLE_CODES for finding in findings)


def _iter_buildable_rows(data: ValidatedData, fc: UploaderFieldsConfig):
    for route_type in (RouteType.SEA, RouteType.RAIL, RouteType.TRUCK):
        frame = data.routes_df[data.routes_df[fc.route_type] == route_type]
        for orig_idx, row in frame.iterrows():
            if _is_buildable(data.row_errors.get((route_type.value, orig_idx), [])):
                yield ("route", route_type, orig_idx, row)
    for orig_idx, row in data.dropp_df.iterrows():
        if _is_buildable(data.row_errors.get(("DROPP", orig_idx), [])):
            yield ("dropp", None, orig_idx, row)


async def _ensure_reference_data(uow: UnitOfWork, data: ValidatedData, fc: UploaderFieldsConfig,
                                 valid_companies: set) -> tuple:
    if data.points_df is not None:
        points_data = await load_points(uow, data.points_df)
    else:
        points_data = []

    hashed_points = {}
    for point in points_data:
        hashed_points[point.city.lower()] = point
        if point.RU_city:
            hashed_points[point.RU_city.lower()] = point

    companies = await load_companies(uow, valid_companies)
    containers = await load_containers(uow, [dict(raw) for raw in REFERENCE_CONTAINERS])
    services = await load_services(uow, data.services_df, fc)
    return hashed_points, companies, containers, services


def _build_routes(data: ValidatedData, fc: UploaderFieldsConfig, stores: tuple,
                  result: SyncResult) -> list:
    hashed_points, companies, containers, services = stores
    routes_lst = []
    for _scope, route_type, orig_idx, row in _iter_buildable_rows(data, fc):
        if route_type is None:
            continue
        try:
            route = create_route(containers, companies, hashed_points, services, row, fc, route_type)
        except Exception as e:
            result.extra_errors.append(_mapped_sync_error(data.document, route_type, orig_idx, e))
            result.skipped_rows += 1
            continue
        if route:
            routes_lst.append(route)
    return routes_lst


def _build_dropp(data: ValidatedData, fc: UploaderFieldsConfig, stores: tuple,
                 result: SyncResult) -> list:
    hashed_points, companies, containers, _services = stores
    dropp_lst = []
    for _scope, route_type, orig_idx, row in _iter_buildable_rows(data, fc):
        if route_type is not None:
            continue
        try:
            drop = create_dropp(containers, companies, hashed_points, row, fc)
        except Exception as e:
            result.extra_errors.append(_mapped_sync_error(data.document, None, orig_idx, e))
            result.skipped_rows += 1
            continue
        if drop:
            dropp_lst.append(drop)
    return dropp_lst


async def sync_validated(uow: UnitOfWork, data: ValidatedData, fc: UploaderFieldsConfig) -> SyncResult:
    result = SyncResult()

    valid_companies = set()
    for _scope, _route_type, _orig_idx, row in _iter_buildable_rows(data, fc):
        valid_companies.add(row[fc.company])
    result.skipped_rows = (
        len(data.routes_df) + len(data.dropp_df)
        - sum(1 for _ in _iter_buildable_rows(data, fc))
    )

    stores = await _ensure_reference_data(uow, data, fc, valid_companies)
    routes_lst = _build_routes(data, fc, stores, result)
    dropp_lst = _build_dropp(data, fc, stores, result)

    result.built_routes = len(routes_lst)
    result.built_dropp_groups = len(dropp_lst)

    await load_routes(uow, routes_lst)
    await load_dropp(uow, dropp_lst)
    return result


async def synchronize(db_session: AsyncSession, frames: dict[str, DataFrame | None],
                      fc: UploaderFieldsConfig, document: str | None,
                      load_on_warnings: bool, points_sheet: str = "points") -> SyncOutcome:
    snapshot = await load_reference_snapshot(db_session)
    validated = validate_frames(
        frames["sea"],
        frames["rail"],
        frames.get("truck"),
        frames["dropp"],
        frames["services"],
        frames.get("points"),
        fc,
        snapshot,
        document=document,
        points_sheet=points_sheet,
    )
    if (validated.report.errors or validated.report.warnings) and not load_on_warnings:
        return SyncOutcome(ok=False, built_routes=0, report=validated.report)

    result = await sync_validated(UnitOfWork(db_session), validated, fc)
    validated.report.errors.extend(result.extra_errors)
    return SyncOutcome(ok=True, built_routes=result.built_routes, report=validated.report)
