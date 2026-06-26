import re
from collections import defaultdict
from typing import Any

import pandas as pd
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from module_data_internal.schemas import (
    ContainerOwner,
    ContainerShipmentTerms,
    ContainerTransferTerms,
    RouteSegmentType,
)
from pandas import DataFrame

from .errors import InvalidRouteSegmentTypeException, LoadingErrorException, PointsWithNanException
from .helpers import format_date, none_filter, price_filter
from .uploader import (
    create_drop_off,
    create_route,
    load_companies,
    load_containers,
    load_drop_off,
    load_points,
    load_routes,
    load_services,
)


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
        processed_df[string_cols_list] = (  # noqa: ECE001
            processed_df[string_cols_list]
            .apply(lambda x: x.str.strip() if x.dtype == "str" else x)
            .apply(remove_extra_spaces)
        )

    if numeric_cols:
        numeric_cols_list = list(numeric_cols)
        processed_df[numeric_cols_list] = processed_df[numeric_cols_list].map(  # noqa: ECE001
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
    processed_df[fields_config.company] = (  # noqa: ECE001
        processed_df[fields_config.company].apply(none_filter).str.strip().str.upper()
    )

    processed_df[fields_config.start_point] = processed_df[fields_config.start_point].apply(none_filter).str.strip()
    processed_df[fields_config.end_point] = processed_df[fields_config.end_point].apply(none_filter).str.strip()
    processed_df[fields_config.terminal] = processed_df[fields_config.terminal].str.strip().str.upper()  # noqa: ECE001

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
    processed_df[fields_config.conversation_percents] = (  # noqa: ECE001
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

    processed_dropp_df = process_points_services_effectivity(processed_dropp_df, warnings, fields_config, "DROP_OFF")
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
        warnings.append(("MissingRouteDataException", missing_info, "DROP_OFF"))

    processed_dropp_df = processed_dropp_df.dropna(subset=df_dropna_subset)

    processed_dropp_df = processed_dropp_df.astype({
        fields_config.container_condition: "str",
    })
    processed_dropp_df.loc[
        processed_dropp_df[fields_config.container_condition].isna(), fields_config.container_condition
    ] = ContainerOwner.COC.value

    return processed_dropp_df


def process_routes_df(processed_routes_df, route_type: RouteSegmentType, warnings, fields_config: UploaderFieldsConfig):
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

    processed_routes_df[fields_config.container_condition] = (
        processed_routes_df[fields_config.container_condition].apply(none_filter)
    )
    processed_routes_df[fields_config.container_transfer_terms] = (
        processed_routes_df[fields_config.container_transfer_terms].apply(none_filter)
    )
    processed_routes_df[fields_config.container_shipment_terms] = (
        processed_routes_df[fields_config.container_shipment_terms].apply(none_filter)
    )

    routes_df_dropna_subset = [
        fields_config.start_point,
        fields_config.end_point,
        fields_config.effective_from,
        fields_config.effective_to,
        fields_config.company,
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

    if route_type is RouteSegmentType.SEA:
        processed_routes_df[fields_config.sea_20dc] = (
            processed_routes_df[fields_config.sea_20dc].apply(price_filter)
        )
        processed_routes_df[fields_config.sea_40hc] = (
            processed_routes_df[fields_config.sea_40hc].apply(price_filter)
        )
    elif route_type is RouteSegmentType.RAIL:
        processed_routes_df[fields_config.rail_40hc] = (
            processed_routes_df[fields_config.rail_40hc].apply(price_filter)
        )
        processed_routes_df[fields_config.rail_20dc24t] = (
            processed_routes_df[fields_config.rail_20dc24t].apply(price_filter)
        )
        processed_routes_df[fields_config.rail_20dc28t] = (
            processed_routes_df[fields_config.rail_20dc28t].apply(price_filter)
        )
    else:
        raise InvalidRouteSegmentTypeException(route_type)

    # Default values
    processed_routes_df = processed_routes_df.astype({
        fields_config.container_condition: "str",
        fields_config.container_transfer_terms: "str",
        fields_config.container_shipment_terms: "str",
    })

    processed_routes_df.loc[
        processed_routes_df[fields_config.container_condition].isna(), fields_config.container_condition
    ] = ContainerOwner.COC.value

    processed_routes_df.loc[
        processed_routes_df[fields_config.container_transfer_terms].isna(), fields_config.container_transfer_terms
    ] = ContainerTransferTerms.FILO.value

    processed_routes_df.loc[
        processed_routes_df[fields_config.container_shipment_terms].isna(), fields_config.container_shipment_terms
    ] = ContainerShipmentTerms.FOR.value

    processed_routes_df[fields_config.route_type] = route_type

    return processed_routes_df


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


async def load_data(  # noqa: C901
    db_session,
    sea_routes_df: DataFrame,
    rail_routes_df: DataFrame,
    dropp_df: DataFrame,
    services_df: DataFrame,
    points_df: DataFrame,
    fields_config: UploaderFieldsConfig,
    load_on_warnings: bool = False,
):
    warnings: list[Any] = []
    # cleanup DF points
    points_df = points_df.apply(lambda x: x.str.strip() if x.dtype == "str" else x)
    points_df = points_df.drop_duplicates(subset=["city", "country"], ignore_index=False)

    points_rows_with_nan = [i + 2 for i in points_df[points_df.isna().any(axis=1)].index.tolist()]  # noqa: ECE001
    if points_rows_with_nan:
        raise PointsWithNanException(points_rows_with_nan)

    # cleanup DF services
    services_df = services_df.apply(lambda x: x.str.strip() if x.dtype == "str" else x)

    services_fingerprint = [
        fields_config.column_name,
        fields_config.service_name,
    ]
    services_df = services_df.dropna(ignore_index=False, subset=services_fingerprint)
    services_df = services_df.drop_duplicates(subset=services_fingerprint, ignore_index=False)

    # process routes and setup new index for correct concatenation
    sea_routes_df = process_routes_df(sea_routes_df, RouteSegmentType.SEA, warnings, fields_config)
    sea_routes_df["Index"] = sea_routes_df.index.to_series()
    sea_routes_df = sea_routes_df.set_index([fields_config.route_type, "Index"])

    rail_routes_df = process_routes_df(rail_routes_df, RouteSegmentType.RAIL, warnings, fields_config)
    rail_routes_df["Index"] = rail_routes_df.index.to_series()
    rail_routes_df = rail_routes_df.set_index([fields_config.route_type, "Index"])

    routes_df: DataFrame = pd.concat((sea_routes_df, rail_routes_df), ignore_index=False)
    del sea_routes_df, rail_routes_df

    # cleanup dropp
    dropp_df = process_dropp_df(dropp_df, warnings, fields_config)

    # Merging points with terminals
    routes_with_terminal = routes_df.dropna(subset=[fields_config.terminal])[[
        fields_config.start_point,
        fields_config.end_point,
        fields_config.terminal,
    ]]
    dropp_with_terminal = dropp_df.dropna(subset=[fields_config.terminal])[[
        fields_config.start_point,
        fields_config.end_point,
        fields_config.terminal,
    ]]

    points_df_merged_with_terminal = pd.concat((
        merge_points_with_terminal(
            points_df,
            routes_with_terminal.loc[[RouteSegmentType.SEA]],
            fields_config,
            fields_config.end_point,
        ),
        merge_points_with_terminal(
            points_df,
            routes_with_terminal.loc[[RouteSegmentType.RAIL]],
            fields_config,
            fields_config.start_point,
        ),
        merge_points_with_terminal(
            points_df,
            dropp_with_terminal,
            fields_config,
            fields_config.start_point,
        ),
    ))

    points_df = pd.concat((
        points_df,
        points_city_concat_terminal(points_df_merged_with_terminal, fields_config),
    )).drop_duplicates()
    del points_df_merged_with_terminal

    # add terminal to the start/end point in routes
    mask = routes_df[fields_config.terminal].notna()
    mask &= routes_df[fields_config.terminal].str.strip() != ""

    sea_mask = (routes_df.index.get_level_values(fields_config.route_type) == RouteSegmentType.SEA) & mask
    routes_df.loc[sea_mask, fields_config.end_point] = (
        routes_df.loc[sea_mask, fields_config.end_point] + " (" + routes_df.loc[sea_mask, fields_config.terminal] + ")"
    )

    rail_mask = (routes_df.index.get_level_values(fields_config.route_type) == RouteSegmentType.RAIL) & mask
    routes_df.loc[rail_mask, fields_config.start_point] = (
        routes_df.loc[rail_mask, fields_config.start_point]
        + " (" + routes_df.loc[rail_mask, fields_config.terminal] + ")"
    )

    # do the same for dropp off
    mask = dropp_df[fields_config.terminal].notna()
    mask &= dropp_df[fields_config.terminal].str.strip() != ""

    dropp_df.loc[mask, fields_config.start_point] = (
        dropp_df.loc[mask, fields_config.start_point] + " (" + dropp_df.loc[mask, fields_config.terminal] + ")"
    )

    # load points
    points_data = await load_points(db_session, points_df) or []
    del points_df

    # hash points
    hashed_points = {}
    for point in points_data:
        hashed_points[point.city.lower()] = hashed_points[point.RU_city.lower()] = point
    points = hashed_points

    # load companies
    companies = await load_companies(
        db_session,
        set(routes_df[fields_config.company].tolist()) | set(dropp_df[fields_config.company].tolist()),
    )

    # load containers
    containers = await load_containers(db_session, [
        {"size": 20, "weight_from": 0, "weight_to": 24, "type": "DC", "name": "20DC≤24t"},
        {"size": 20, "weight_from": 24, "weight_to": 28, "type": "DC", "name": "20DC 24-28t"},
        {"size": 40, "weight_from": 0, "weight_to": 28, "type": "HC", "name": "40HC≤28t"},
    ])

    # load services
    services = await load_services(db_session, services_df, fields_config)
    del services_df

    # load routes
    routes_lst = []

    for index, row in routes_df.iterrows():
        route_type, i = index
        try:
            route = create_route(containers, companies, points, services, row, fields_config, route_type)
        except (LoadingErrorException, ValueError) as e:
            warnings.append((e, i, route_type))
            continue

        if route:
            routes_lst.append(route)

    del routes_df

    # load dropp
    dropp_lst = []

    for i, row in dropp_df.iterrows():
        try:
            drop = create_drop_off(containers, companies, points, row, fields_config)
        except (LoadingErrorException, ValueError) as e:
            warnings.append((e, i, None))
            continue

        if drop:
            dropp_lst.append(drop)

    del dropp_df

    if warnings and not load_on_warnings:
        return False, len(routes_lst), warnings

    await load_routes(db_session, routes_lst)
    await load_drop_off(db_session, dropp_lst)
    return True, len(routes_lst), warnings
