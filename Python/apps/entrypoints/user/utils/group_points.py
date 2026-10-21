import re
from dataclasses import dataclass, field
from typing import Any

_id_type = int | str


@dataclass
class Company:
    id: _id_type  # noqa: A003
    name: str


@dataclass
class Translation:
    """Translation for a point includes country"""
    name: str
    country: str


@dataclass
class PortTranslation:
    """Translation for a port (only name, no country)."""
    name: str


_translations_map = dict[str, Translation]
_port_translations_map = dict[str, PortTranslation | None]


@dataclass
class RawPoint:
    """Raw input point with a single company."""
    id: _id_type  # noqa: A003
    company: Company
    translates: _translations_map = field(default_factory=dict)


@dataclass
class GroupedPoint:
    """Point after company grouping – contains all companies and IDs for a given full name."""
    ids: set[int] = field(default_factory=set)
    external_ids: set[str] = field(default_factory=set)
    companies: list[Company] = field(default_factory=list)
    translates: _translations_map = field(default_factory=dict)


@dataclass
class GroupedPort:
    ids: set[int] = field(default_factory=set)
    external_ids: set[str] = field(default_factory=set)
    companies: list[Company] = field(default_factory=list)
    translates: _port_translations_map = field(default_factory=dict)


@dataclass
class GroupedPointWithPort:
    """Final point after port grouping. Contains all original IDs that map to this base point."""
    ids: set[int] = field(default_factory=set)
    external_ids: set[str] = field(default_factory=set)
    companies: list[Company] = field(default_factory=list)
    translates: _translations_map = field(default_factory=dict)
    ports: list[GroupedPort] = field(default_factory=list)


def _extract_port_from_name(name: str) -> tuple[str, str | None]:
    """Extracts port name from parentheses at the end of the string."""
    match = re.search(r"\s*\(([^)]+)\)\s*$", name)
    if not match:
        return name, None

    port = match.group(1).strip()
    point = re.sub(r"\s*\([^)]+\)\s*$", "", name).strip()
    return point, port


def _extract_ports_from_all_translates(point: GroupedPoint) -> tuple[_translations_map, _port_translations_map]:
    point_translates: _translations_map = {}
    port_translates: _port_translations_map = {}

    for lang, translation in point.translates.items():
        point_name, port_name = _extract_port_from_name(translation.name)
        if not port_name:
            continue

        point_translates[lang] = Translation(
            name=point_name,
            country=translation.country,
        )
        port_translates[lang] = PortTranslation(name=port_name)

    return point_translates, port_translates


def _convert_point_to_port(point: GroupedPoint) -> tuple[GroupedPort, _translations_map]:
    """
    Converts a point to port
    :param point: a point descriptor
    :return: object with replaced translations
    """
    point_translates, port_translates = _extract_ports_from_all_translates(point)
    translates: _port_translations_map = {}
    result = GroupedPort(
        ids=point.ids,
        external_ids=point.external_ids,
        translates=translates,
        companies=point.companies,
    )

    for lang, port_translate in port_translates.items():
        if not port_translate:
            continue

        translates[lang] = port_translate

    return result, point_translates


def _extend_grouped_point_with_port(base_point: GroupedPointWithPort, point: GroupedPoint):
    for internal_id in point.ids:
        base_point.ids.add(internal_id)
    for external_id in point.external_ids:
        base_point.external_ids.add(external_id)

    base_point.companies.extend(point.companies)


def group_companies(
    points: list[RawPoint],
    external_companies: set | None = None,
    base_lang: str = "ru",
) -> list[GroupedPoint]:
    result: dict[str, GroupedPoint] = {}
    if not external_companies:
        external_companies = set()

    for point in points:
        key = point.translates[base_lang].name

        if key in result:
            result[key].companies.append(point.company)
            if point.company.id in external_companies:
                result[key].external_ids.add(str(point.id))
            else:
                result[key].ids.add(int(point.id))
        else:
            if point.company.id in external_companies:
                item = GroupedPoint(
                    external_ids={str(point.id)},
                    companies=[point.company],
                    translates=point.translates,
                )
            else:
                item = GroupedPoint(
                    ids={int(point.id)},
                    companies=[point.company],
                    translates=point.translates,
                )
            result[key] = item

    return list(result.values())


def group_transfers(
    grouped_by_company_points: list[GroupedPoint],
    excluded_company_ids: set[_id_type] | None = None,
    base_lang: str = "ru",
) -> list[GroupedPointWithPort]:
    if not excluded_company_ids:
        excluded_company_ids = set()

    result: dict[str, GroupedPointWithPort] = {}

    for point in grouped_by_company_points:
        excluded = False
        for company in point.companies:
            if company.id in excluded_company_ids:
                excluded = True
                break

        if excluded:
            if point.translates[base_lang].name in result:
                _extend_grouped_point_with_port(result[point.translates[base_lang].name], point)
            else:
                result[point.translates[base_lang].name] = GroupedPointWithPort(
                    ids=point.ids,
                    external_ids=point.external_ids,
                    companies=point.companies,
                    translates=point.translates,
                )
            continue

        point_name, port_name = _extract_port_from_name(point.translates[base_lang].name)
        if port_name:
            if point_name in result:
                result[point_name].ports.append(_convert_point_to_port(point)[0])
            else:
                port_descriptor, point_translates = _convert_point_to_port(point)
                result[point_name] = GroupedPointWithPort(
                    ports=[port_descriptor],
                    translates=point_translates,
                )

        elif point_name in result:
            _extend_grouped_point_with_port(result[point_name], point)
        else:
            result[point_name] = GroupedPointWithPort(
                ids=point.ids,
                external_ids=point.external_ids,
                companies=point.companies,
                translates=point.translates,
            )

    return list(result.values())


def raw_point_from_dict(data: dict[str, Any]) -> RawPoint:
    """Converts a raw input dictionary to a RawPoint object."""
    company = Company(id=data["company"]["id"], name=data["company"]["name"])
    translates = {}
    for lang, trans in data["translates"].items():
        translates[lang] = Translation(name=trans["name"], country=trans["country"])

    return RawPoint(id=data["id"], company=company, translates=translates)
