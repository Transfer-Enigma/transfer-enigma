import pandas as pd
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from backend_admin.service.routes_loading.rules import ReferenceSnapshot
from pandas import DataFrame


def make_fc(**overrides) -> UploaderFieldsConfig:
    data = {
        name: name
        for name, field in UploaderFieldsConfig.model_fields.items()
        if field.is_required()
    }
    data["effective_from"] = "effective_from"
    data["effective_to"] = "effective_to"
    data.update(overrides)
    return UploaderFieldsConfig(**data)


def _physical_columns(fc: UploaderFieldsConfig) -> list[str]:
    columns = [
        value for value in fc.model_dump(exclude={"services", "services_with_container"}).values()
        if isinstance(value, str)
    ]
    for service in list(fc.services) + list(fc.services_with_container):
        columns.append(getattr(fc, service))
        columns.append(getattr(fc, f"{service}_currency"))
    return columns


def make_frame(fc: UploaderFieldsConfig, rows: list[dict]) -> DataFrame:
    base = dict.fromkeys(_physical_columns(fc))
    return pd.DataFrame([{**base, **row} for row in rows])


def clean_sea_row(fc: UploaderFieldsConfig, **overrides) -> dict:
    row = {
        fc.start_point: "Vladivostok",
        fc.end_point: "Moscow",
        fc.effective_from: "2026-01-01",
        fc.effective_to: "2026-12-31",
        fc.company: "fesco",
        fc.container_transfer_terms: "filo",
        fc.container_shipment_terms: "for",
        fc.container_condition: "coc",
        fc.sea_20dc: 100.0,
        fc.sea_40hc: 200.0,
        fc.sea_20dc_currency: "USD",
        fc.sea_40hc_currency: "USD",
        fc.is_through: True,
        fc.conversation_percents: 0,
    }
    row.update(overrides)
    return row


def clean_dropp_row(fc: UploaderFieldsConfig, **overrides) -> dict:
    row = {
        fc.start_point: "Vladivostok",
        fc.end_point: "Moscow",
        fc.effective_from: "2026-01-01",
        fc.effective_to: "2026-12-31",
        fc.company: "fesco",
        fc.container_condition: "coc",
        fc.drop20: 50.0,
        fc.conversation_percents: 0,
    }
    row.update(overrides)
    return row


def make_points_frame(**overrides) -> DataFrame:
    rows = [{
        "city": "Vladivostok",
        "country": "RU",
        "RU_city": "Владивосток",
        "RU_country": "РФ",
    }]
    rows[0].update(overrides)
    return pd.DataFrame(rows)


def make_services_frame(fc: UploaderFieldsConfig, rows: list[dict] | None = None) -> DataFrame:
    if rows is None:
        rows = []
    return pd.DataFrame(rows, columns=[fc.column_name, fc.service_name, fc.description, fc.including])


def make_snapshot(companies=("FESCO",), points=("vladivostok", "moscow", "владивосток"),
                  services=(), existing_row_uids=()) -> ReferenceSnapshot:
    return ReferenceSnapshot(
        companies=frozenset(companies),
        point_keys=frozenset(points),
        services=frozenset(services),
        existing_row_uids=frozenset(existing_row_uids),
    )
