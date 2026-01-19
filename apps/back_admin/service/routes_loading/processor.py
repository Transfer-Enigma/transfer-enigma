from collections import defaultdict

import pandas as pd

from .errors import LoadingErrorException, PointsWithNanException
from .helpers import cond_filter, format_date, none_filter, price_filter
from .uploader import create_route, load_containers, load_points, load_routes, load_services


async def load_data(db_session, routes_df, points_df, fields_config, load_on_warnings=False):
    warnings = []
    # cleanup DF
    # points
    points_df = points_df.apply(lambda x: x.str.strip())
    points_df = points_df.apply(lambda x: x.str.title())
    points_df = points_df.drop_duplicates(subset=["city", "country"], ignore_index=False)

    points_rows_with_nan = [i + 2 for i in points_df[points_df.isna().any(axis=1)].index.tolist()]
    if points_rows_with_nan:
        raise PointsWithNanException(points_rows_with_nan)

    # routes
    routes_df = routes_df[routes_df.columns.intersection(fields_config.values())]

    numeric_cols = {
        fields_config["sea_20dc"],
        fields_config["sea_40hc"],
        fields_config["rail_40hc"],
        fields_config["rail_20dc24t"],
        fields_config["rail_20dc28t"],
        fields_config["conversation_percents"],
        fields_config["drop20"],
        fields_config["drop40"],
    }

    string_cols = [col for col in routes_df.columns if col not in numeric_cols]
    numeric_cols = [col for col in numeric_cols if col in routes_df.columns]

    if string_cols:
        routes_df[string_cols] = routes_df[string_cols].apply(lambda x: x.str.strip())

    if numeric_cols:
        routes_df[numeric_cols] = routes_df[numeric_cols].map(
            lambda x: x.strip() if isinstance(x, str) else x
        )

    routes_df[fields_config["start_point"]] = routes_df[fields_config["start_point"]].apply(none_filter)
    routes_df[fields_config["end_point"]] = routes_df[fields_config["end_point"]].apply(none_filter)
    routes_df[fields_config["effective_from"]] = routes_df[fields_config["effective_from"]].apply(none_filter)
    routes_df[fields_config["effective_to"]] = routes_df[fields_config["effective_to"]].apply(none_filter)
    routes_df[fields_config["container_condition"]] = routes_df[fields_config["container_condition"]].apply(none_filter)
    routes_df[fields_config["service"]] = routes_df[fields_config["service"]].apply(none_filter)
    routes_df[fields_config["conversation_percents"]] = (
        routes_df[fields_config["conversation_percents"]].apply(
            lambda x: x.strip().rstrip('%').rstrip() if isinstance(x, str) else x * 100 if isinstance(x, float) else x
        )
    )

    routes_df_dropna_subset = [
        fields_config["start_point"],
        fields_config["end_point"],
        fields_config["effective_from"],
        fields_config["effective_to"],
        fields_config["condition"],
        fields_config["container_condition"],
        fields_config["service"],
    ]
    missing_info_about_id = defaultdict(list)

    for col in routes_df_dropna_subset:
        missing_idx = routes_df[routes_df[col].isna()].index.tolist()
        for _id in missing_idx:
            missing_info_about_id[_id].append(col)

    missing_info = tuple(
        {"row_index": row_id, "skipped_columns": columns}
        for row_id, columns in missing_info_about_id.items()
    )

    if missing_info:
        warnings.append(("MissingRoutesDataException", missing_info))

    routes_df = routes_df.dropna(subset=routes_df_dropna_subset)

    routes_df[fields_config["start_point"]] = routes_df[fields_config["start_point"]].str.title()
    routes_df[fields_config["end_point"]] = routes_df[fields_config["end_point"]].str.title()
    routes_df[fields_config["transit"]] = routes_df[fields_config["transit"]].str.title()
    routes_df[fields_config["type"]] = routes_df[fields_config["type"]].str.lower()
    routes_df[fields_config["service"]] = routes_df[fields_config["service"]].str.upper()

    routes_df[fields_config["condition"]] = routes_df[fields_config["condition"]].apply(cond_filter)

    routes_df[fields_config["sea_20dc"]] = routes_df[fields_config["sea_20dc"]].apply(price_filter)
    routes_df[fields_config["sea_40hc"]] = routes_df[fields_config["sea_40hc"]].apply(price_filter)
    routes_df[fields_config["rail_40hc"]] = routes_df[fields_config["rail_40hc"]].apply(price_filter)
    routes_df[fields_config["rail_20dc24t"]] = routes_df[fields_config["rail_20dc24t"]].apply(price_filter)
    routes_df[fields_config["rail_20dc28t"]] = routes_df[fields_config["rail_20dc28t"]].apply(price_filter)

    # load services
    services = await load_services(db_session, set(routes_df[fields_config["service"]].tolist()))

    # load containers
    containers = await load_containers(db_session, [
        {"size": 20, "weight_from": 0, "weight_to": 24, "type": "DC", "name": "20DC≤24t"},
        {"size": 20, "weight_from": 24, "weight_to": 28, "type": "DC", "name": "20DC 24-28t"},
        {"size": 40, "weight_from": 0, "weight_to": 28, "type": "HC", "name": "40HC≤28t"},
    ])

    # load points
    routes_with_transit = routes_df.dropna(subset=[fields_config["transit"]])[[
        fields_config["type"],
        fields_config["start_point"],
        fields_config["end_point"],
        fields_config["transit"],
    ]]

    points_df_merged_with_transit = pd.concat((
        pd.merge(
            points_df.copy(),
            routes_with_transit[routes_with_transit[fields_config["type"]] == "море"][[
                fields_config["end_point"],
                fields_config["transit"],
            ]],
            left_on="city",
            right_on=fields_config["end_point"],
        ),
        pd.merge(
            points_df.copy(),
            routes_with_transit[routes_with_transit[fields_config["type"]] == "море"][[
                fields_config["end_point"],
                fields_config["transit"],
            ]],
            left_on="RU_city",
            right_on=fields_config["end_point"],
        ),
        pd.merge(
            points_df.copy(),
            routes_with_transit[routes_with_transit[fields_config["type"]] == "жд"][[
                fields_config["start_point"],
                fields_config["transit"],
            ]],
            left_on="city",
            right_on=fields_config["start_point"],
        ),
        pd.merge(
            points_df.copy(),
            routes_with_transit[routes_with_transit[fields_config["type"]] == "жд"][[
                fields_config["start_point"],
                fields_config["transit"],
            ]],
            left_on="RU_city",
            right_on=fields_config["start_point"],
        ),
    ))

    points_df_merged_with_transit = points_df_merged_with_transit[list(
        set(points_df_merged_with_transit.columns)
        - {fields_config["start_point"], fields_config["end_point"]}
    )].drop_duplicates()
    points_df_merged_with_transit["city"] = (
        points_df_merged_with_transit["city"] + " (" + points_df_merged_with_transit[fields_config["transit"]] + ")"
    )

    points_df_merged_with_transit["RU_city"] = (
        points_df_merged_with_transit["RU_city"] + " (" + points_df_merged_with_transit[fields_config["transit"]] + ")"
    )
    points_df_merged_with_transit = points_df_merged_with_transit[list(
        set(points_df_merged_with_transit.columns)
        - {fields_config["transit"]}
    )]

    points_df = pd.concat((points_df, points_df_merged_with_transit)).drop_duplicates()
    points = await load_points(db_session, points_df) or []
    del points_df, routes_with_transit, points_df_merged_with_transit
    # hash points
    hashed_points = {}
    for point in points:
        hashed_points[point.city] = hashed_points[point.RU_city] = point
    points = hashed_points

    # parse dates
    routes_df[fields_config["effective_from"]] = routes_df[fields_config["effective_from"]].apply(format_date)
    routes_df[fields_config["effective_to"]] = routes_df[fields_config["effective_to"]].apply(format_date)
    routes_df_dropna_subset = [
        fields_config["effective_from"],
        fields_config["effective_to"],
    ]

    missing_idx = []

    for col in routes_df_dropna_subset:
        missing_idx += routes_df[routes_df[col].isna()].index.tolist()

    if missing_idx:
        warnings.append(("UnsupportedDateFormat", tuple(row_idx for row_idx in missing_idx)))

    routes_df = routes_df.dropna(ignore_index=False, subset=routes_df_dropna_subset)

    # parse transit
    # sea
    mask = routes_df[fields_config["transit"]].notna() & (routes_df[fields_config["type"]] == "море")
    routes_df.loc[mask, fields_config["end_point"]] = (
        routes_df.loc[mask, fields_config["end_point"]]
        + " ("
        + routes_df.loc[mask, fields_config["transit"]]
        + ")"
    )
    # rail
    mask = routes_df[fields_config["transit"]].notna() & (routes_df[fields_config["type"]] == "жд")
    routes_df.loc[mask, fields_config["start_point"]] = (
        routes_df.loc[mask, fields_config["start_point"]]
        + " ("
        + routes_df.loc[mask, fields_config["transit"]]
        + ")"
    )
    # mixed
    mask = routes_df[fields_config["transit"]].notna() & (routes_df[fields_config["type"]] == "море+жд")
    routes_df.loc[mask, fields_config["comment"]] = (
        "< Via "
        + routes_df.loc[mask, fields_config["transit"]]
        + " > "
        + routes_df.loc[mask, fields_config["comment"]].fillna("")
    )

    # load routes
    routes_lst = []

    for _, row in routes_df.iterrows():
        try:
            route_drop = create_route(containers, services, points, row, fields_config)
        except LoadingErrorException as e:
            warnings.append(e)
            continue

        if route_drop:
            routes_lst.append(route_drop)

    del routes_df
    if warnings and not load_on_warnings:
        return False, len(routes_lst), warnings

    await load_routes(db_session, routes_lst)
    return True, len(routes_lst), warnings
