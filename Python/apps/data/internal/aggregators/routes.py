import asyncio
import datetime
import logging

from data.cache.settings import get_setting_cached
from data.repositories.routes import build_queries, execute_query
from shared.database import Base, get_database
from shared.dto.route import RouteResult
from shared.orm.drop import DropModel
from shared.orm.route import RouteModel
from shared.setting_definitions import get_setting_definition

from .transformers.routes import transform_routes

logger = logging.getLogger(__name__)


def process_results(
    results: list[list[list[Base]] | BaseException],
    date: datetime.date,
    container_ids: list[int],
) -> list[tuple[list[Base], bool]]:
    """Keep the rows of the queries, without the services of the other containers."""
    flat_result: list = []

    for result in results:
        if not result or isinstance(result, BaseException):
            if isinstance(result, BaseException):
                logger.error("Route query failed", exc_info=result)
            continue

        for row in result:
            if not row:
                continue

            routes: list[RouteModel] = row[:-1] if not row[-1] or isinstance(row[-1], DropModel) else row

            for segment in routes:
                # TODO: find another way...
                segment.services = [
                    service for service in segment.services
                    if service.container_id is None or service.container_id in container_ids
                ]

            flat_result.append((row, False))

    return flat_result


_flags: list[tuple[str, str]] = [
    ("hide-sea-soc", "hide_sea_soc"),
    ("rail-direct", "rail_direct"),
    ("sea-direct", "sea_direct"),
    ("sea-rail", "sea_rail"),
    ("rail-sea", "rail_sea"),
    ("head-truck", "head_truck"),
    ("tail-truck", "tail_truck"),
]


async def find_all_paths(
    date: datetime.date,
    start_point_id: int,
    end_point_id: int,
    container_ids: list[int],
    *,
    head_truck: bool = False,
    tail_truck: bool = False,
) -> list[RouteResult]:
    flag_values: dict[str, bool] = {}

    async with get_database().session_context() as session:
        for name, local_name in _flags:
            try:
                setting = await get_setting_cached("feature-flag", name, session=session)
                if setting is not None:
                    flag_values[local_name] = bool(setting.value)
                    continue
            except Exception:
                logger.warning(
                    f"Failed to read feature-flag {name}, use the default value\nException info:",
                    exc_info=True,
                )

            setting_def = get_setting_definition("feature-flag", name)
            if not setting_def:
                raise RuntimeError("Feature flag " + name + " not found")

            flag_values[local_name] = bool(setting_def.true_type_default)

    all_queries = build_queries(
        date, start_point_id, end_point_id, container_ids,
        head_truck=head_truck,
        tail_truck=tail_truck,
        feature_head_truck=flag_values["head_truck"],
        feature_tail_truck=flag_values["tail_truck"],
        rail_direct=flag_values["rail_direct"],
        sea_direct=flag_values["sea_direct"],
        sea_rail=flag_values["sea_rail"],
        rail_sea=flag_values["rail_sea"],
        hide_sea_soc=flag_values["hide_sea_soc"],
    )

    coroutines = [execute_query(query) for query in all_queries]
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    return transform_routes(process_results(results, date, container_ids))
