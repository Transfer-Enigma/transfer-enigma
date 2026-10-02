from dataclasses import dataclass, field

import pandas as pd
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from backend_admin.service.routes_loading.error_reporting import (
    parse_all_warning_types,
    parse_error,
    to_sync_error,
)
from backend_admin.service.routes_loading.errors import LoadingErrorException
from backend_admin.service.routes_loading.processor import (
    merge_points_with_terminal,
    points_city_concat_terminal,
    process_dropp_df,
    process_routes_df,
)
from backend_admin.service.routes_loading.rules import (
    ReferenceSnapshot,
    RowContext,
    RulesReport,
    run_row_rules,
)
from backend_admin.service.routes_loading.sync_errors import SyncError, SyncErrorCode, make_error
from module_shared.schemas.company import CompanyModel
from module_shared.schemas.container import ContainerModel, ContainerType
from module_shared.schemas.drop import DropModel
from module_shared.schemas.point import PointModel
from module_shared.schemas.route import RouteModel, RouteType
from module_shared.schemas.service import ServiceModel
from pandas import DataFrame
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from .dedupe import find_duplicate_groups, row_payload_uid
from .uid import extract_uids, natural_uid_for_dropp_values, natural_uid_for_route_values
from .uploader import ContainerRawType, create_dropp, create_route

REFERENCE_CONTAINERS: list[ContainerRawType] = [
    {"size": 20, "weight_from": 0, "weight_to": 24, "type": "DC", "name": "20DC≤24t"},
    {"size": 20, "weight_from": 24, "weight_to": 28, "type": "DC", "name": "20DC 24-28t"},
    {"size": 40, "weight_from": 0, "weight_to": 28, "type": "HC", "name": "40HC≤28t"},
]

SHEET_LABELS = {
    RouteType.SEA: "МОРЕ",
    RouteType.RAIL: "ЖД",
    RouteType.TRUCK: "АВТО",
    None: "ДРОПП",
}


@dataclass
class ValidationReport:
    errors: list[SyncError] = field(default_factory=list)
    warnings: list[SyncError] = field(default_factory=list)
    checked_rows: int = 0

    def to_dict(self) -> dict:
        return {
            "errors": [error.model_dump() for error in self.errors],
            "warnings": [warning.model_dump() for warning in self.warnings],
            "checked_rows": self.checked_rows,
        }


@dataclass
class ValidatedData:
    report: ValidationReport
    routes_df: DataFrame
    dropp_df: DataFrame
    points_df: DataFrame | None
    services_df: DataFrame | None
    row_errors: dict[tuple[str, int], list[SyncError]]
    document: str | None = None
    row_uids: dict[tuple[str, int], str] = field(default_factory=dict)


def _row_values(row, fc: UploaderFieldsConfig, route_type: RouteType | None) -> dict:
    def _cell(column: str):
        if column not in row.index:
            return None
        value = row[column]
        if value is None:
            return None
        try:
            is_missing = pd.isna(value)
        except (TypeError, ValueError):
            is_missing = False
        return None if is_missing else value

    if route_type is None:
        return {
            "start_point": _cell(fc.start_point),
            "end_point": _cell(fc.end_point),
            "company": _cell(fc.company),
            "effective_from": _cell(fc.effective_from),
            "effective_to": _cell(fc.effective_to),
        }
    return {
        "type": route_type.value,
        "company": _cell(fc.company),
        "start_point": _cell(fc.start_point),
        "end_point": _cell(fc.end_point),
        "dropp_off_point": _cell(fc.dropp_off_point),
        "effective_from": _cell(fc.effective_from),
        "effective_to": _cell(fc.effective_to),
        "container_shipment_terms": _cell(fc.container_shipment_terms),
        "container_transfer_terms": _cell(fc.container_transfer_terms),
        "container_owner": _cell(fc.container_condition),
        "is_through": _cell(fc.is_through),
    }


async def load_reference_snapshot(db_session: AsyncSession) -> ReferenceSnapshot:
    company_names = (await db_session.execute(select(CompanyModel.name))).scalars().all()
    point_rows = (await db_session.execute(select(PointModel.city, PointModel.RU_city))).all()
    service_names = (await db_session.execute(select(ServiceModel.internal_name))).scalars().all()

    point_keys = set()
    for city, ru_city in point_rows:
        point_keys.add(city.lower())
        if ru_city:
            point_keys.add(ru_city.lower())

    return ReferenceSnapshot(
        companies=frozenset(name.upper() for name in company_names),
        point_keys=frozenset(point_keys),
        services=frozenset(service_names),
        existing_row_uids=await _existing_row_uids(db_session),
    )


async def _existing_row_uids(db_session: AsyncSession) -> frozenset[str]:
    uids = set()
    routes = (await db_session.execute(select(RouteModel).options(
        joinedload(RouteModel.company),
        joinedload(RouteModel.start_point),
        joinedload(RouteModel.end_point),
        joinedload(RouteModel.dropp_off_point),
    ))).scalars().all()
    for route in routes:
        uids.add(natural_uid_for_route_values({
            "type": route.type,
            "company": route.company.name,
            "start_point": route.start_point.city,
            "end_point": route.end_point.city,
            "dropp_off_point": route.dropp_off_point.city if route.dropp_off_point else None,
            "effective_from": route.effective_from,
            "effective_to": route.effective_to,
            "container_shipment_terms": route.container_shipment_terms,
            "container_transfer_terms": route.container_transfer_terms,
            "container_owner": route.container_owner,
            "is_through": route.is_through,
        }))
    drops = (await db_session.execute(select(DropModel).options(
        joinedload(DropModel.start_point),
        joinedload(DropModel.end_point),
        joinedload(DropModel.company),
    ))).scalars().all()
    for item in drops:
        uids.add(natural_uid_for_dropp_values({
            "start_point": item.start_point.city if item.start_point else None,
            "end_point": item.end_point.city if item.end_point else None,
            "company": item.company.name,
            "effective_from": item.effective_from,
            "effective_to": item.effective_to,
        }))
    return frozenset(uids)


def _stub_stores(snapshot: ReferenceSnapshot) -> tuple:
    companies = {name: CompanyModel(name=name) for name in snapshot.companies}
    points = {
        key: PointModel(city=key, country="", RU_city=None, RU_country=None)
        for key in snapshot.point_keys
    }
    services = {
        name: ServiceModel(name=name, internal_name=name, description="", mandatory=False, default=False)
        for name in snapshot.services
    }
    containers = {}
    for container in REFERENCE_CONTAINERS:
        key = (container["size"], container["weight_from"], container["weight_to"])
        containers[key] = ContainerModel(
            size=container["size"],
            weight_from=container["weight_from"],
            weight_to=container["weight_to"],
            type=ContainerType(container["type"]),
            name=container["name"],
        )
    return containers, companies, points, services


def _trial_build_route(containers, companies, points, services, row, fc, route_type, ctx) -> SyncError | None:
    try:
        create_route(containers, companies, points, services, row, fc, route_type)
    except Exception as e:  # Validate must never crash on a broken row, report it instead.
        if isinstance(e, (LoadingErrorException, ValueError, KeyError, AttributeError)):
            parsed = parse_error(e, ctx.row_number - 2, route_type, document=ctx.document)
            finding = to_sync_error(parsed)
        else:
            finding = make_error(
                SyncErrorCode.UNKNOWN,
                document=ctx.document,
                sheet=ctx.sheet,
                row=ctx.row_number,
                type=type(e).__name__,
                detail=str(e),
            )
        finding.sheet = SHEET_LABELS[route_type]
        finding.row = ctx.row_number
        return finding
    return None


def _trial_build_dropp(containers, companies, points, row, fc, ctx) -> SyncError | None:
    try:
        create_dropp(containers, companies, points, row, fc)
    except Exception as e:  # Validate must never crash on a broken row, report it instead.
        if isinstance(e, (LoadingErrorException, ValueError, KeyError, AttributeError)):
            parsed = parse_error(e, ctx.row_number - 2, None, document=ctx.document)
            finding = to_sync_error(parsed)
        else:
            finding = make_error(
                SyncErrorCode.UNKNOWN,
                document=ctx.document,
                sheet=ctx.sheet,
                row=ctx.row_number,
                type=type(e).__name__,
                detail=str(e),
            )
        finding.sheet = SHEET_LABELS[None]
        finding.row = ctx.row_number
        return finding
    return None


def _validate_route_row(row, route_type, orig_idx, containers, companies, points,
                        services, fc, snapshot, document) -> list[SyncError]:
    ctx = RowContext(
        row=row,
        fields_config=fc,
        snapshot=snapshot,
        sheet=SHEET_LABELS[route_type],
        row_number=orig_idx + 2,
        route_type=route_type,
        scope="route",
        document=document,
    )
    findings = run_row_rules(ctx)
    if not findings:
        trial = _trial_build_route(containers, companies, points, services, row, fc, route_type, ctx)
        if trial is not None:
            findings.append(trial)
    return findings


def _validate_dropp_row(row, orig_idx, containers, companies, points,
                        fc, snapshot, document) -> list[SyncError]:
    ctx = RowContext(
        row=row,
        fields_config=fc,
        snapshot=snapshot,
        sheet=SHEET_LABELS[None],
        row_number=orig_idx + 2,
        route_type=None,
        scope="dropp",
        document=document,
    )
    findings = run_row_rules(ctx)
    if not findings:
        trial = _trial_build_dropp(containers, companies, points, row, fc, ctx)
        if trial is not None:
            findings.append(trial)
    return findings


def _extend_snapshot_with_terminals(snapshot: ReferenceSnapshot, points_df: DataFrame | None,
                                    routes_df: DataFrame, dropp_df: DataFrame,
                                    fc: UploaderFieldsConfig) -> tuple[ReferenceSnapshot, DataFrame | None]:
    if points_df is None:
        return snapshot, points_df

    parts = []
    if {fc.start_point, fc.end_point, fc.terminal, fc.route_type} <= set(routes_df.columns):
        routes_with_terminal = routes_df.dropna(subset=[fc.terminal])[
            [fc.start_point, fc.end_point, fc.terminal, fc.route_type]
        ]
        parts.append(merge_points_with_terminal(
            points_df,
            routes_with_terminal[routes_with_terminal[fc.route_type] == RouteType.SEA],
            fc,
            fc.end_point,
        ))
        parts.append(merge_points_with_terminal(
            points_df,
            routes_with_terminal[routes_with_terminal[fc.route_type] == RouteType.RAIL],
            fc,
            fc.start_point,
        ))
    if {fc.start_point, fc.end_point, fc.terminal} <= set(dropp_df.columns):
        dropp_with_terminal = dropp_df.dropna(subset=[fc.terminal])[
            [fc.start_point, fc.end_point, fc.terminal]
        ]
        parts.append(merge_points_with_terminal(
            points_df,
            dropp_with_terminal,
            fc,
            fc.start_point,
        ))
    if not parts:
        return snapshot, points_df

    merged = pd.concat(parts)
    suffixed = points_city_concat_terminal(merged, fc)
    extra_keys = set(suffixed["city"].str.lower().tolist())
    if "RU_city" in suffixed.columns:
        extra_keys |= set(suffixed["RU_city"].dropna().str.lower().tolist())

    points_with_terminals = pd.concat((points_df, suffixed)).drop_duplicates()

    return ReferenceSnapshot(
        companies=snapshot.companies,
        point_keys=snapshot.point_keys | frozenset(extra_keys),
        services=snapshot.services,
        existing_row_uids=snapshot.existing_row_uids,
    ), points_with_terminals


def _append_terminals(routes_df: DataFrame, dropp_df: DataFrame, fc: UploaderFieldsConfig):
    routes_df = routes_df.copy()
    dropp_df = dropp_df.copy()

    if {fc.terminal, fc.route_type, fc.start_point, fc.end_point} <= set(routes_df.columns):
        mask = routes_df[fc.terminal].notna() & (routes_df[fc.terminal].str.strip() != "")

        sea_mask = (routes_df[fc.route_type] == RouteType.SEA) & mask
        routes_df.loc[sea_mask, fc.end_point] = (
            routes_df.loc[sea_mask, fc.end_point]
            + " (" + routes_df.loc[sea_mask, fc.terminal] + ")"
        )

        rail_mask = (routes_df[fc.route_type] == RouteType.RAIL) & mask
        routes_df.loc[rail_mask, fc.start_point] = (
            routes_df.loc[rail_mask, fc.start_point]
            + " (" + routes_df.loc[rail_mask, fc.terminal] + ")"
        )

    if {fc.terminal, fc.start_point} <= set(dropp_df.columns):
        mask = dropp_df[fc.terminal].notna() & (dropp_df[fc.terminal].str.strip() != "")
        dropp_df.loc[mask, fc.start_point] = (
            dropp_df.loc[mask, fc.start_point] + " (" + dropp_df.loc[mask, fc.terminal] + ")"
        )

    return routes_df, dropp_df


def _duplicate_finding(document: str | None, sheet: str, orig_idx: int, uid_column: str) -> SyncError:
    return make_error(
        SyncErrorCode.DUPLICATE_ROW,
        document=document,
        sheet=sheet,
        row=orig_idx + 2,
        cell=uid_column,
    )


def _collect_duplicate_findings(routes_df: DataFrame, dropp_df: DataFrame, fc: UploaderFieldsConfig,
                                all_route_dfs: list, document: str | None,
                                uid_column: str) -> tuple[set, list]:
    dup_keys: set[tuple[str, int]] = set()
    findings: list[SyncError] = []
    for route_type, _ in all_route_dfs:
        pairs = [
            ((route_type.value, orig_idx), row_payload_uid(row, fc, route_type))
            for orig_idx, row in routes_df[routes_df[fc.route_type] == route_type].iterrows()
        ]
        for _uid, keys in find_duplicate_groups(pairs).items():
            for scope, orig_idx in keys[1:]:
                dup_keys.add((scope, orig_idx))
                findings.append(_duplicate_finding(document, SHEET_LABELS[route_type], orig_idx, uid_column))
    dropp_pairs = [
        (("DROPP", orig_idx), row_payload_uid(row, fc, None))
        for orig_idx, row in dropp_df.iterrows()
    ]
    for _uid, keys in find_duplicate_groups(dropp_pairs).items():
        for scope, orig_idx in keys[1:]:
            dup_keys.add((scope, orig_idx))
            findings.append(_duplicate_finding(document, SHEET_LABELS[None], orig_idx, uid_column))
    return dup_keys, findings


def _check_points_frame(points_df: DataFrame | None, document: str | None,
                        points_sheet: str) -> tuple[DataFrame | None, SyncError | None]:
    if points_df is None:
        return None, None
    points_df = points_df.apply(lambda x: x.str.strip() if x.dtype == "str" else x)
    points_df = points_df.drop_duplicates(subset=["city", "country"], ignore_index=False)
    points_rows_with_nan = [i + 2 for i in points_df[points_df.isna().any(axis=1)].index.tolist()]
    if points_rows_with_nan:
        finding = make_error(
            SyncErrorCode.POINTS_SHEET_NAN,
            document=document,
            sheet=points_sheet,
        )
        finding.details = {"row_numbers": points_rows_with_nan}
        return points_df, finding
    return points_df, None


def _import_legacy_warnings(report: RulesReport, legacy_warnings: list,
                            fc: UploaderFieldsConfig, document: str | None) -> None:
    for converted in parse_all_warning_types(legacy_warnings, fc, document=document):
        base = {
            key: value for key, value in converted.items()
            if key in SyncError.model_fields and key != "details"
        }
        extras = {
            key: value for key, value in converted.items()
            if key not in SyncError.model_fields and key != "error"
        }
        finding = SyncError(**base, details=extras or None)
        if finding.sheet in ("SEA", "RAIL", "TRUCK", "DROPP"):
            finding.sheet = {"SEA": "МОРЕ", "RAIL": "ЖД", "TRUCK": "АВТО", "DROPP": "ДРОПП"}[finding.sheet]
        report.add(finding)


def _sanitize_route_frames(sea_routes_df: DataFrame | None, rail_routes_df: DataFrame | None,
                           truck_routes_df: DataFrame | None, dropp_df: DataFrame | None,
                           fc: UploaderFieldsConfig,
                           legacy_warnings: list) -> tuple[list, DataFrame, DataFrame]:
    all_route_dfs = []
    if sea_routes_df is not None and not sea_routes_df.empty:
        all_route_dfs.append((
            RouteType.SEA,
            process_routes_df(sea_routes_df, RouteType.SEA, legacy_warnings, fc),
        ))
    if rail_routes_df is not None and not rail_routes_df.empty:
        all_route_dfs.append((
            RouteType.RAIL,
            process_routes_df(rail_routes_df, RouteType.RAIL, legacy_warnings, fc),
        ))
    if truck_routes_df is not None and not truck_routes_df.empty:
        all_route_dfs.append((
            RouteType.TRUCK,
            process_routes_df(truck_routes_df, RouteType.TRUCK, legacy_warnings, fc),
        ))

    if dropp_df is not None and not dropp_df.empty:
        dropp_df = process_dropp_df(dropp_df, legacy_warnings, fc)
    else:
        dropp_df = pd.DataFrame(columns=[fc.terminal])

    if all_route_dfs:
        routes_df: DataFrame = pd.concat(
            [routes for _, routes in all_route_dfs],
            ignore_index=False,
        )
    else:
        routes_df = pd.DataFrame(columns=[fc.route_type])
    # NOTE: terminals are appended by the caller after _extend_snapshot_with_terminals,
    # which matches pre-append point names against the points sheet.
    return all_route_dfs, routes_df, dropp_df


def validate_frames(
    sea_routes_df: DataFrame | None,
    rail_routes_df: DataFrame | None,
    truck_routes_df: DataFrame | None,
    dropp_df: DataFrame | None,
    services_df: DataFrame | None,  # Accepted for signature parity with load_data; service rows need no validation yet.
    points_df: DataFrame | None,
    fields_config: UploaderFieldsConfig,
    snapshot: ReferenceSnapshot,
    document: str | None = None,
    points_sheet: str = "points",
    uid_column: str = "__uid",
) -> ValidatedData:
    report = RulesReport()
    fc = fields_config

    existing_uids = {
        ("SEA", idx): uid
        for idx, uid in extract_uids(sea_routes_df, uid_column).items()
    } | {
        ("RAIL", idx): uid
        for idx, uid in extract_uids(rail_routes_df, uid_column).items()
    } | {
        ("TRUCK", idx): uid
        for idx, uid in extract_uids(truck_routes_df, uid_column).items()
    } | {
        ("DROPP", idx): uid
        for idx, uid in extract_uids(dropp_df, uid_column).items()
    }

    points_df, points_fatal = _check_points_frame(points_df, document, points_sheet)
    if points_fatal is not None:
        report.add(points_fatal)
        return ValidatedData(
            report=ValidationReport(
                errors=report.errors,
                warnings=report.warnings,
                checked_rows=0,
            ),
            routes_df=pd.DataFrame(columns=[fc.route_type]),
            dropp_df=pd.DataFrame(columns=[fc.terminal]),
            points_df=points_df,
            services_df=services_df,
            row_errors={},
            document=document,
        )

    legacy_warnings: list = []
    all_route_dfs, routes_df, dropp_df = _sanitize_route_frames(
        sea_routes_df, rail_routes_df, truck_routes_df, dropp_df, fc, legacy_warnings,
    )

    _import_legacy_warnings(report, legacy_warnings, fc, document)

    snapshot, points_df = _extend_snapshot_with_terminals(snapshot, points_df, routes_df, dropp_df, fc)
    routes_df, dropp_df = _append_terminals(routes_df, dropp_df, fc)

    containers, companies, points, services = _stub_stores(snapshot)

    row_errors: dict[tuple[str, int], list[SyncError]] = {}
    row_uids: dict[tuple[str, int], str] = {}
    dup_keys, dup_findings = _collect_duplicate_findings(
        routes_df, dropp_df, fc, all_route_dfs, document, uid_column,
    )
    report.extend(dup_findings)

    for route_type, _ in all_route_dfs:
        for orig_idx, row in routes_df[routes_df[fc.route_type] == route_type].iterrows():
            if (route_type.value, orig_idx) in dup_keys:
                continue
            findings = _validate_route_row(
                row, route_type, orig_idx, containers, companies, points,
                services, fc, snapshot, document,
            )
            report.extend(findings)
            if findings:
                row_errors[(route_type.value, orig_idx)] = findings
            row_uids[(route_type.value, orig_idx)] = existing_uids.get(
                (route_type.value, orig_idx),
                natural_uid_for_route_values(_row_values(row, fc, route_type)),
            )

    for orig_idx, row in dropp_df.iterrows():
        if ("DROPP", orig_idx) in dup_keys:
            continue
        findings = _validate_dropp_row(
            row, orig_idx, containers, companies, points, fc, snapshot, document,
        )
        report.extend(findings)
        if findings:
            row_errors[("DROPP", orig_idx)] = findings
        row_uids[("DROPP", orig_idx)] = existing_uids.get(
            ("DROPP", orig_idx),
            natural_uid_for_dropp_values(_row_values(row, fc, None)),
        )

    checked_rows = len(routes_df) + len(dropp_df)

    return ValidatedData(
        report=ValidationReport(errors=report.errors, warnings=report.warnings, checked_rows=checked_rows),
        routes_df=routes_df,
        dropp_df=dropp_df,
        points_df=points_df,
        services_df=services_df,
        row_errors=row_errors,
        document=document,
        row_uids=row_uids,
    )
