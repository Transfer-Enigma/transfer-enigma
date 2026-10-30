from shared.exceptions.routes_loading import (
    CompanyNotFoundException,
    InvalidDroppRow,
    InvalidRouteConditionException,
    InvalidRouteTypeException,
    NoPriceInRouteException,
    PointNotFoundException,
)
from shared.models.upoader_fields_config import UploaderFieldsConfig
from shared.orm import RouteType


def parse_error(error, row_number, routes_ws_type):
    row_number += 2
    routes_ws_map = {
        RouteType.SEA: "МОРЕ",
        RouteType.RAIL: "ЖД",
        RouteType.TRUCK: "АВТО",
        None: "ДРОПП",
    }
    routes_ws = routes_ws_map.get(routes_ws_type, "Неизвестный")

    if isinstance(error, InvalidRouteConditionException):
        return f"Неверные условия поставки: '{error.condition}' (лист {routes_ws}, строка {row_number})"

    elif isinstance(error, PointNotFoundException):
        return f"Не найден город или порт: '{error.error_key}' (лист {routes_ws}, строка {row_number})"

    elif isinstance(error, CompanyNotFoundException):
        return f"Не найдена компания: '{error.error_key}' (лист {routes_ws}, строка {row_number})"

    elif isinstance(error, InvalidRouteTypeException):
        return f"Неверный тип маршрута: '{error.route_type}' (лист {routes_ws}, строка {row_number})"

    elif isinstance(error, NoPriceInRouteException):
        return f"Отсутствуют цены в маршруте (лист {routes_ws}, строка {row_number})"

    elif isinstance(error, InvalidDroppRow):
        return f"Неверный формат данных в листе {routes_ws} на строке {row_number}"

    return f"Неизвестная ошибка {type(error).__name__}: '{error}' (лист {routes_ws}, строка {row_number})"


def parse_warning(key, value, routes_ws_name, fields_config: UploaderFieldsConfig):
    if key == "MissingRoutesDataException":
        missing_info_parsed = []
        for invalid_row in value:
            row_number = invalid_row["row_index"] + 2
            missing_info_parsed.append({
                "error": f"Ошибка в листе {routes_ws_name} на строке {row_number} в следующих ячейках:",
                "row_number": row_number,
                "columns": invalid_row["skipped_columns"],
            })

        return {
            "error": f"Ошибка в листе {routes_ws_name}: не заполнены обязательные столбцы "
                     f"в следующих строках ({len(value)}):",
            "rows_list": missing_info_parsed,
        }

    elif key == "UnsupportedDateFormat":
        return {
            "error": f"Ошибка в листе {routes_ws_name}: неподдерживаемый формат столбцов "
                     f"{fields_config.effective_from}/{fields_config.effective_to}:",
            "row_numbers": [i + 2 for i in value],
        }

    return {
        "error": f"Неизвестная ошибка '{key}' в листе {routes_ws_name}",
        "row_numbers": [i + 2 for i in value],
    }


def parse_all_warning_types(warnings, fc):
    return list({
        parse_error(err[0], err[1], err[2])
        for err in warnings
        if issubclass(type(err[0]), Exception)
    }) + [
        parse_warning(warning[0], warning[1], warning[2], fc)
        for warning in warnings
        if not issubclass(type(warning[0]), Exception)
    ]
