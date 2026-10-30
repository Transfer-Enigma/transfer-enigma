from dataclasses import dataclass, field

id_type = int | str


@dataclass
class Company:
    id: id_type  # noqa: A003
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


translations_map_type = dict[str, Translation]
port_translations_map_type = dict[str, PortTranslation | None]


@dataclass
class RawPoint:
    """Raw input point with a single company."""
    id: id_type  # noqa: A003
    company: Company
    translates: translations_map_type = field(default_factory=dict)


@dataclass
class GroupedPoint:
    """Point after company grouping – contains all companies and IDs for a given full name."""
    ids: set[int] = field(default_factory=set)
    external_ids: set[str] = field(default_factory=set)
    companies: list[Company] = field(default_factory=list)
    translates: translations_map_type = field(default_factory=dict)


@dataclass
class GroupedPort:
    ids: set[int] = field(default_factory=set)
    external_ids: set[str] = field(default_factory=set)
    companies: list[Company] = field(default_factory=list)
    translates: port_translations_map_type = field(default_factory=dict)


@dataclass
class GroupedPointWithPort:
    """Final point after port grouping. Contains all original IDs that map to this base point."""
    ids: set[int] = field(default_factory=set)
    external_ids: set[str] = field(default_factory=set)
    companies: list[Company] = field(default_factory=list)
    translates: translations_map_type = field(default_factory=dict)
    ports: list[GroupedPort] = field(default_factory=list)
