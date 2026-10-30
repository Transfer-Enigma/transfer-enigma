from collections.abc import Iterable
from typing import Any

from shared.dto.point import PointItem


def _is_invalid_point(point: dict[str, Any]) -> bool:
    point_loc_name = point.get("name")
    return not point_loc_name or "DEFAULT LOCATION" in point_loc_name


def _transform_point(point: dict[str, Any]) -> PointItem | None:
    if _is_invalid_point(point):
        return None

    language_map = {
        "ru": {"name_field": "name", "country_field": "country"},
        "en": {"name_field": "nameLatin", "country_field": "countryLatin"},
        "cn": {"name_field": "nameCN", "country_field": "countryCN"},
        "vn": {"name_field": "nameVN", "country_field": "countryVN"},
    }

    result: PointItem = {
        "id": point["id"],
        "company": {"id": "FESCO", "name": "FESCO"},
        "translates": {},
    }

    for lang_code, fields in language_map.items():
        name_value = point.get(fields["name_field"])
        if name_value is None:
            continue
        country_value = point.get(fields["country_field"])
        result["translates"][lang_code] = {
            "country": country_value.strip() if country_value is not None else "",
            "name": name_value.strip(),
        }

    return result


def transform_points(points: Iterable[dict[str, Any]]) -> Iterable[PointItem]:
    return filter(None, map(_transform_point, points))
