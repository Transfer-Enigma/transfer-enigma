from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from backend_admin.service.routes_loading.sync_errors import (
    Severity,
    SyncError,
    SyncErrorCode,
    make_error,
)
from module_shared.schemas.route import (
    ContainerOwner,
    ContainerShipmentTerms,
    ContainerTransferTerms,
    RouteType,
)

from .uid import natural_uid_for_dropp_values, natural_uid_for_route_values

Scope = Literal["route", "dropp", "any"]


@dataclass(frozen=True)
class ReferenceSnapshot:
    companies: frozenset[str]
    point_keys: frozenset[str]
    services: frozenset[str]
    existing_row_uids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RowContext:
    row: Any
    fields_config: UploaderFieldsConfig
    snapshot: ReferenceSnapshot
    sheet: str
    row_number: int
    route_type: RouteType | None
    scope: Scope
    document: str | None = None


@dataclass(frozen=True)
class ValidationRule:
    code: SyncErrorCode
    check: Callable[[RowContext], SyncError | None]
    severity: Severity = "error"
    scope: Scope = "any"
    fields: tuple[str, ...] = ()


RULES: list[ValidationRule] = []


def rule(code: SyncErrorCode, severity: Severity = "error", scope: Scope = "any",
         fields: tuple[str, ...] = ()):
    def decorator(fn: Callable[[RowContext], SyncError | None]) -> Callable[[RowContext], SyncError | None]:
        RULES.append(ValidationRule(code=code, check=fn, severity=severity, scope=scope, fields=fields))
        return fn

    return decorator


def _missing_columns(ctx: RowContext, columns: list[str]) -> list[str]:
    return [col for col in columns if col in ctx.row.index and pd.isna(ctx.row[col])]


def _required_route_columns(ctx: RowContext) -> list[str]:
    fc = ctx.fields_config
    return [col for col in (
        fc.start_point,
        fc.end_point,
        fc.effective_from,
        fc.effective_to,
        fc.company,
    ) if col in ctx.row.index]


def _required_dropp_columns(ctx: RowContext) -> list[str]:
    fc = ctx.fields_config
    return [col for col in (
        fc.start_point,
        fc.end_point,
        fc.effective_from,
        fc.effective_to,
        fc.company,
    ) if col in ctx.row.index]


@rule(SyncErrorCode.REQUIRED_CELL_EMPTY, severity="warning", scope="route")
def required_route_cells(ctx: RowContext) -> SyncError | None:
    missing = _missing_columns(ctx, _required_route_columns(ctx))
    if not missing:
        return None
    return make_error(
        SyncErrorCode.REQUIRED_CELL_EMPTY,
        document=ctx.document,
        sheet=ctx.sheet,
        row=ctx.row_number,
        cell=", ".join(missing),
        severity="warning",
        count=len(missing),
    )


@rule(SyncErrorCode.REQUIRED_CELL_EMPTY, severity="warning", scope="dropp")
def required_dropp_cells(ctx: RowContext) -> SyncError | None:
    missing = _missing_columns(ctx, _required_dropp_columns(ctx))
    if not missing:
        return None
    return make_error(
        SyncErrorCode.REQUIRED_CELL_EMPTY,
        document=ctx.document,
        sheet=ctx.sheet,
        row=ctx.row_number,
        cell=", ".join(missing),
        severity="warning",
        count=len(missing),
    )


@rule(SyncErrorCode.BAD_DATE_FORMAT, severity="warning")
def valid_effective_dates(ctx: RowContext) -> SyncError | None:
    fc = ctx.fields_config
    bad = _missing_columns(ctx, [c for c in (fc.effective_from, fc.effective_to) if c in ctx.row.index])
    if not bad:
        return None
    return make_error(
        SyncErrorCode.BAD_DATE_FORMAT,
        document=ctx.document,
        sheet=ctx.sheet,
        row=ctx.row_number,
        cell=bad[0],
        severity="warning",
        col_from=fc.effective_from,
        col_to=fc.effective_to,
    )


@rule(SyncErrorCode.BAD_ENUM_VALUE, scope="route")
def valid_container_terms(ctx: RowContext) -> SyncError | None:
    fc = ctx.fields_config
    for column, enum_cls, field_name in (
        (fc.container_transfer_terms, ContainerTransferTerms, "условия передачи контейнера"),
        (fc.container_shipment_terms, ContainerShipmentTerms, "условия поставки"),
        (fc.container_condition, ContainerOwner, "принадлежность контейнера"),
    ):
        if column not in ctx.row.index:
            continue
        value = ctx.row[column]
        if pd.isna(value):
            continue
        try:
            enum_cls(str(value).upper())
        except ValueError:
            return make_error(
                SyncErrorCode.BAD_ENUM_VALUE,
                document=ctx.document,
                sheet=ctx.sheet,
                row=ctx.row_number,
                cell=column,
                value=value,
                field=field_name,
            )
    return None


@rule(SyncErrorCode.BAD_ENUM_VALUE, scope="route")
def valid_route_type(ctx: RowContext) -> SyncError | None:
    if ctx.route_type in (RouteType.SEA, RouteType.RAIL, RouteType.TRUCK):
        return None
    return make_error(
        SyncErrorCode.BAD_ENUM_VALUE,
        document=ctx.document,
        sheet=ctx.sheet,
        row=ctx.row_number,
        value=ctx.route_type,
        field="тип маршрута",
    )


@rule(SyncErrorCode.COMPANY_NOT_FOUND)
def known_company(ctx: RowContext) -> SyncError | None:
    column = ctx.fields_config.company
    if column not in ctx.row.index or pd.isna(ctx.row[column]):
        return None
    key = str(ctx.row[column]).strip().upper()
    if not key:
        return None
    if key in ctx.snapshot.companies:
        return None
    return make_error(
        SyncErrorCode.COMPANY_NOT_FOUND,
        document=ctx.document,
        sheet=ctx.sheet,
        row=ctx.row_number,
        cell=column,
        key=ctx.row[column],
    )


@rule(SyncErrorCode.POINT_NOT_FOUND)
def known_points(ctx: RowContext) -> SyncError | None:
    fc = ctx.fields_config
    columns = [c for c in (fc.start_point, fc.end_point, fc.dropp_off_point) if c in ctx.row.index]
    for column in columns:
        value = ctx.row[column]
        if pd.isna(value) or not str(value).strip():
            continue
        if str(value).strip().lower() not in ctx.snapshot.point_keys:
            return make_error(
                SyncErrorCode.POINT_NOT_FOUND,
                document=ctx.document,
                sheet=ctx.sheet,
                row=ctx.row_number,
                cell=column,
                key=value,
            )
    return None


def _route_price_columns(ctx: RowContext) -> list[str]:
    fc = ctx.fields_config
    if ctx.route_type is RouteType.SEA:
        return [fc.sea_20dc, fc.sea_40hc]
    if ctx.route_type is RouteType.RAIL:
        return [fc.rail_20dc24t, fc.rail_20dc28t, fc.rail_40hc]
    if ctx.route_type is RouteType.TRUCK:
        return [fc.truck_20dc, fc.truck_40hc]
    return []


@rule(SyncErrorCode.NO_PRICE, scope="route")
def route_has_price(ctx: RowContext) -> SyncError | None:
    if ctx.route_type not in (RouteType.SEA, RouteType.RAIL, RouteType.TRUCK):
        return None
    columns = [c for c in _route_price_columns(ctx) if c in ctx.row.index]
    if any(pd.notna(ctx.row[col]) for col in columns):
        return None
    return make_error(
        SyncErrorCode.NO_PRICE,
        document=ctx.document,
        sheet=ctx.sheet,
        row=ctx.row_number,
    )


@rule(SyncErrorCode.DROPP_ROW_INVALID, scope="dropp")
def valid_dropp_row(ctx: RowContext) -> SyncError | None:
    fc = ctx.fields_config
    company = ctx.row[fc.company] if fc.company in ctx.row.index else None
    effective_from = ctx.row[fc.effective_from] if fc.effective_from in ctx.row.index else None
    effective_to = ctx.row[fc.effective_to] if fc.effective_to in ctx.row.index else None
    if company and not pd.isna(company) and effective_from is not None and effective_to is not None:
        return None
    return make_error(
        SyncErrorCode.DROPP_ROW_INVALID,
        document=ctx.document,
        sheet=ctx.sheet,
        row=ctx.row_number,
    )


def run_row_rules(ctx: RowContext) -> list[SyncError]:
    findings = []
    for validation_rule in RULES:
        if validation_rule.scope != "any" and validation_rule.scope != ctx.scope:
            continue
        finding = validation_rule.check(ctx)
        if finding is not None:
            findings.append(finding)
    return findings


def row_natural_uid(ctx: RowContext) -> str:
    values = {
        "type": ctx.route_type.value if ctx.route_type is not None else None,
        "company": _ctx_cell(ctx, ctx.fields_config.company),
        "start_point": _ctx_cell(ctx, ctx.fields_config.start_point),
        "end_point": _ctx_cell(ctx, ctx.fields_config.end_point),
        "dropp_off_point": _ctx_cell(ctx, ctx.fields_config.dropp_off_point),
        "effective_from": _ctx_cell(ctx, ctx.fields_config.effective_from),
        "effective_to": _ctx_cell(ctx, ctx.fields_config.effective_to),
        "container_shipment_terms": _ctx_cell(ctx, ctx.fields_config.container_shipment_terms),
        "container_transfer_terms": _ctx_cell(ctx, ctx.fields_config.container_transfer_terms),
        "container_owner": _ctx_cell(ctx, ctx.fields_config.container_condition),
        "is_through": _ctx_cell(ctx, ctx.fields_config.is_through),
    }
    if ctx.scope == "dropp":
        return natural_uid_for_dropp_values(values)
    return natural_uid_for_route_values(values)


def _ctx_cell(ctx: RowContext, column: str):
    if column not in ctx.row.index:
        return None
    value = ctx.row[column]
    if value is None:
        return None
    with suppress(TypeError, ValueError):
        if pd.isna(value):
            return None
    return value


@rule(SyncErrorCode.UID_NOT_IN_DB, scope="any")
def uid_known_in_db(ctx: RowContext) -> SyncError | None:
    if not ctx.snapshot.existing_row_uids:
        return None
    uid = row_natural_uid(ctx)
    if uid in ctx.snapshot.existing_row_uids:
        return None
    return make_error(
        SyncErrorCode.UID_NOT_IN_DB,
        document=ctx.document,
        sheet=ctx.sheet,
        row=ctx.row_number,
        cell=ctx.fields_config.uid_column if hasattr(ctx.fields_config, "uid_column") else None,
        uid=uid,
    )


@dataclass
class RulesReport:
    errors: list[SyncError] = field(default_factory=list)
    warnings: list[SyncError] = field(default_factory=list)

    def add(self, finding: SyncError) -> None:
        if finding.severity == "warning":
            self.warnings.append(finding)
        else:
            self.errors.append(finding)

    def extend(self, findings: list[SyncError]) -> None:
        for finding in findings:
            self.add(finding)
