import re
from collections import defaultdict

import pandas as pd
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from module_shared.schemas.route import (
    ContainerOwner,
    ContainerShipmentTerms,
    ContainerTransferTerms,
    RouteType,
)
from pandas import DataFrame

from .errors import InvalidRouteTypeException
from .helpers import format_date, none_filter, price_filter


def remove_extra_spaces(value):
    if isinstance(value, str):
        return re.sub(r" {2,}", " ", value.strip())
    return value


def select_cols(processed_df: DataFrame, cols: list[str]):
    return processed_df[processed_df.columns.intersection(cols)]


def process_numeric_and_string_cols(processed_df: DataFrame, numeric_cols: set[str]):
    string_cols = {col for col in processed_df.columns if col not in numeric_cols}
    numeric_cols = {col for col in numeric_cols if col in processed_df.columns}

    if string_cols:
        string_cols_list = list(string_cols)
        processed_df[string_cols_list] = (
            processed_df[string_cols_list]
            .apply(lambda x: x.str.strip() if x.dtype == "str" else x)
            .apply(remove_extra_spaces)
        )

    if numeric_cols:
        numeric_cols_list = list(numeric_cols)
        processed_df[numeric_cols_list] = processed_df[numeric_cols_list].map(
            lambda x: (
                x.replace("%", "").replace("$", "").replace(" ", "")
                if isinstance(x, str) else x
            )
        )

    return processed_df


def process_points_services_effectivity(
    processed_df: DataFrame,
    warnings,
    fields_config:
    UploaderFieldsConfig,
    ws_name: str,
):
    processed_df[fields_config.company] = (
        processed_df[fields_config.company].apply(none_filter).str.strip().str.upper()
    )

    processed_df[fields_config.start_point] = processed_df[fields_config.start_point].apply(none_filter).str.strip()
    processed_df[fields_config.end_point] = processed_df[fields_config.end_point].apply(none_filter).str.strip()
    if fields_config.terminal in processed_df.columns:
        processed_df[fields_config.terminal] = processed_df[fields_config.terminal].str.strip().str.upper()

    if fields_config.dropp_off_point in processed_df.columns:
        processed_df[fields_config.dropp_off_point] = (
            processed_df[fields_config.dropp_off_point].apply(none_filter).str.strip()
        )

    processed_df[fields_config.effective_from] = (
        processed_df[fields_config.effective_from].apply(none_filter).apply(format_date)
    )
    processed_df[fields_config.effective_to] = (
        processed_df[fields_config.effective_to].apply(none_filter).apply(format_date)
    )

    # remove rows without dates
    df_dropna_subset = [
        fields_config.effective_from,
        fields_config.effective_to,
    ]

    missing_idx = []
    for col in df_dropna_subset:
        missing_idx += processed_df[processed_df[col].isna()].index.tolist()

    if missing_idx:
        warnings.append(("UnsupportedDateFormat", tuple(row_idx for row_idx in missing_idx), ws_name))

    return processed_df.dropna(ignore_index=False, subset=df_dropna_subset)


def process_conversion_percents(processed_df: DataFrame, fields_config: UploaderFieldsConfig):
    if fields_config.conversation_percents not in processed_df.columns:
        return processed_df
    processed_df[fields_config.conversation_percents] = (
        processed_df[fields_config.conversation_percents].apply(
            lambda x: (
                remove_extra_spaces(x.strip()).rstrip("%").rstrip()
                if isinstance(x, str) else
                x * 100 if isinstance(x, float) else x
            )
        )
    )
    return processed_df


def process_dropp_df(processed_dropp_df: DataFrame, warnings, fields_config: UploaderFieldsConfig):
    processed_dropp_df = select_cols(
        processed_dropp_df,
        fields_config.model_dump(exclude={"services", "services_with_container"}).values(),
    )
    processed_dropp_df = process_numeric_and_string_cols(
        processed_dropp_df,
        {
            fields_config.drop20,
            fields_config.drop40,
            fields_config.conversation_percents,
        },
    )

    processed_dropp_df[fields_config.drop20] = processed_dropp_df[fields_config.drop20].apply(price_filter)
    processed_dropp_df[fields_config.drop40] = processed_dropp_df[fields_config.drop40].apply(price_filter)

    processed_dropp_df = process_points_services_effectivity(processed_dropp_df, warnings, fields_config, "DROPP")
    processed_dropp_df = process_conversion_percents(processed_dropp_df, fields_config)
    processed_dropp_df[fields_config.container_condition] = (
        processed_dropp_df[fields_config.container_condition].apply(none_filter)
    )

    missing_info_about_id = defaultdict(list)
    df_dropna_subset = [
        fields_config.start_point,
        fields_config.end_point,
        fields_config.effective_from,
        fields_config.effective_to,
        fields_config.company,
    ]

    for col in df_dropna_subset:
        missing_idx = processed_dropp_df[processed_dropp_df[col].isna()].index.tolist()
        for _id in missing_idx:
            missing_info_about_id[_id].append(col)

    missing_info = tuple(
        {"row_index": row_id, "skipped_columns": columns}
        for row_id, columns in missing_info_about_id.items()
    )

    if missing_info:
        warnings.append(("MissingRoutesDataException", missing_info, "DROPP"))

    processed_dropp_df = processed_dropp_df.dropna(subset=df_dropna_subset)

    processed_dropp_df = processed_dropp_df.astype({
        fields_config.container_condition: "str",
    })
    processed_dropp_df.loc[
        processed_dropp_df[fields_config.container_condition].isna(), fields_config.container_condition
    ] = ContainerOwner.COC.value

    return processed_dropp_df


def process_routes_df(processed_routes_df, route_type: RouteType, warnings, fields_config: UploaderFieldsConfig):
    processed_routes_df = select_cols(
        processed_routes_df,
        fields_config.model_dump(exclude={"services", "services_with_container"}).values(),
    )

    processed_routes_df = process_numeric_and_string_cols(
        processed_routes_df,
        {
            fields_config.sea_20dc,
            fields_config.sea_40hc,
            fields_config.rail_40hc,
            fields_config.rail_20dc24t,
            fields_config.rail_20dc28t,
            fields_config.truck_20dc,
            fields_config.truck_40hc,
            fields_config.conversation_percents,
            *(getattr(fields_config, service_column) for service_column in fields_config.services),
            *(getattr(fields_config, service_column) for service_column in fields_config.services_with_container),
        },
    )

    processed_routes_df = process_points_services_effectivity(
        processed_routes_df,
        warnings,
        fields_config,
        route_type.value,
    )
    processed_routes_df = process_conversion_percents(processed_routes_df, fields_config)

    routes_df_dropna_subset = [
        col for col in [
            fields_config.start_point,
            fields_config.end_point,
            fields_config.effective_from,
            fields_config.effective_to,
            fields_config.company,
        ] if col in processed_routes_df.columns
    ]
    missing_info_about_id = defaultdict(list)

    for col in routes_df_dropna_subset:
        missing_idx = processed_routes_df[processed_routes_df[col].isna()].index.tolist()
        for _id in missing_idx:
            missing_info_about_id[_id].append(col)

    missing_info = tuple(
        {"row_index": row_id, "skipped_columns": columns}
        for row_id, columns in missing_info_about_id.items()
    )

    if missing_info:
        warnings.append(("MissingRoutesDataException", missing_info, route_type.value))

    processed_routes_df = processed_routes_df.dropna(subset=routes_df_dropna_subset)

    if route_type is RouteType.SEA:
        processed_routes_df[fields_config.sea_20dc] = (
            processed_routes_df[fields_config.sea_20dc].apply(price_filter)
        )
        processed_routes_df[fields_config.sea_40hc] = (
            processed_routes_df[fields_config.sea_40hc].apply(price_filter)
        )
    elif route_type is RouteType.RAIL:
        processed_routes_df[fields_config.rail_40hc] = (
            processed_routes_df[fields_config.rail_40hc].apply(price_filter)
        )
        processed_routes_df[fields_config.rail_20dc24t] = (
            processed_routes_df[fields_config.rail_20dc24t].apply(price_filter)
        )
        processed_routes_df[fields_config.rail_20dc28t] = (
            processed_routes_df[fields_config.rail_20dc28t].apply(price_filter)
        )
    elif route_type is RouteType.TRUCK:
        processed_routes_df[fields_config.truck_20dc] = (
            processed_routes_df[fields_config.truck_20dc].apply(price_filter)
        )
        processed_routes_df[fields_config.truck_40hc] = (
            processed_routes_df[fields_config.truck_40hc].apply(price_filter)
        )
    else:
        raise InvalidRouteTypeException(route_type)

    _apply_route_defaults(processed_routes_df, route_type, fields_config)
    _normalize_string_columns(processed_routes_df, fields_config)

    processed_routes_df[fields_config.route_type] = route_type

    return processed_routes_df


def _ensure_column(df: DataFrame, col_name: str, default_value=None, fillna_value=None):
    if col_name not in df.columns:
        df[col_name] = default_value
    elif fillna_value is not None:
        df[col_name] = df[col_name].fillna(fillna_value)


def _apply_route_defaults(df: DataFrame, route_type: RouteType, fc: UploaderFieldsConfig):
    container_defaults = [
        (fc.container_condition, ContainerOwner.COC.value),
        (fc.container_transfer_terms, ContainerTransferTerms.FILO.value),
        (fc.container_shipment_terms, ContainerShipmentTerms.FOR.value),
    ]

    for col_name, default in container_defaults:
        if col_name in df.columns:
            df[col_name] = df[col_name].fillna(default).astype(str)
        else:
            df[col_name] = default

    _ensure_column(df, fc.is_through, True, True)
    _ensure_column(df, fc.conversation_percents, 0, 0)

    for col_name in [fc.dropp_off_point, fc.comment, fc.timetable]:
        _ensure_column(df, col_name)

    match route_type:
        case RouteType.TRUCK:
            price_cols = [fc.truck_20dc_currency, fc.truck_40hc_currency]
        case RouteType.SEA:
            price_cols = [fc.sea_20dc_currency, fc.sea_40hc_currency]
        case RouteType.RAIL:
            price_cols = [fc.rail_20dc24t_currency, fc.rail_20dc28t_currency, fc.rail_40hc_currency]
        case _:
            price_cols = []

    for price_col in price_cols:
        _ensure_column(df, price_col, "РУБ", "РУБ")


def _normalize_string_columns(df: DataFrame, fc: UploaderFieldsConfig):
    df[fc.company] = (
        df[fc.company]
        .astype("string")
        .str.strip()
        .str.upper()
    )
    df[fc.start_point] = df[fc.start_point].astype("string").str.strip()
    df[fc.end_point] = df[fc.end_point].astype("string").str.strip()


def merge_points_with_terminal(
    points_df: DataFrame,
    data_df: DataFrame,
    fields_config: UploaderFieldsConfig,
    concat_field: str,
):
    return pd.concat((
        pd.merge(
            points_df.copy(),
            data_df[[concat_field, fields_config.terminal]],
            left_on="city",
            right_on=concat_field,
        ),
        pd.merge(
            points_df.copy(),
            data_df[[concat_field, fields_config.terminal]],
            left_on="RU_city",
            right_on=concat_field,
        ),
    ))


def points_city_concat_terminal(points_df_merged_with_terminal: DataFrame, fields_config: UploaderFieldsConfig):
    points_df_merged_with_terminal = points_df_merged_with_terminal[list(
        set(points_df_merged_with_terminal.columns)
        - {fields_config.start_point, fields_config.end_point}
    )].drop_duplicates()

    points_df_merged_with_terminal["city"] = (
        points_df_merged_with_terminal["city"]
        + " ("
        + points_df_merged_with_terminal[fields_config.terminal]
        + ")"
    )
    points_df_merged_with_terminal["RU_city"] = (
        points_df_merged_with_terminal["RU_city"]
        + " ("
        + points_df_merged_with_terminal[fields_config.terminal]
        + ")"
    )

    return points_df_merged_with_terminal[list(
        set(points_df_merged_with_terminal.columns)
        - {fields_config.terminal}
    )]
