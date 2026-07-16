import json
from dataclasses import dataclass, field
from typing import Any

from module_shared.schemas.setting import SettingType


@dataclass(frozen=True)
class SettingDefinition:
    group: str
    name: str
    value_type: SettingType
    true_type_default: Any
    description: str
    locked: bool = field(default=True, kw_only=True)

    @property
    def default(self) -> str:
        match self.true_type_default:
            case str():
                return self.true_type_default
            case bool():
                return str(self.true_type_default).lower()
            case dict() | list():
                return json.dumps(self.true_type_default)
            case _:
                return str(self.true_type_default)


SETTING_DEFINITIONS: list[SettingDefinition] = [
    SettingDefinition(
        group="feature-flag",
        name="hide-sea-soc",
        value_type=SettingType.BOOL,
        true_type_default=False,
        description="Hide sea SOC segments from combined sea+rail route calculation",
    ),
    SettingDefinition(
        group="feature-flag",
        name="rail-direct",
        value_type=SettingType.BOOL,
        true_type_default=True,
        description="Enable RAIL direct route calculation",
    ),
    SettingDefinition(
        group="feature-flag",
        name="sea-direct",
        value_type=SettingType.BOOL,
        true_type_default=True,
        description="Enable SEA direct route calculation",
    ),
    SettingDefinition(
        group="feature-flag",
        name="sea-rail",
        value_type=SettingType.BOOL,
        true_type_default=True,
        description="Enable SEA→RAIL combined route calculation",
    ),
    SettingDefinition(
        group="feature-flag",
        name="rail-sea",
        value_type=SettingType.BOOL,
        true_type_default=False,  # TODO: make 'True' when logic will be production-ready
        description="Enable RAIL→SEA combined route calculation",
    ),
    SettingDefinition(
        group="feature-flag",
        name="demo-excluded-fields",
        value_type=SettingType.JSON,
        true_type_default=["company"],
        description="List of fields to blur for demo users",
    ),
]


def get_setting_definitions() -> list[SettingDefinition]:
    return SETTING_DEFINITIONS


def get_setting_definition(group: str, name: str) -> SettingDefinition | None:
    for defn in SETTING_DEFINITIONS:
        if defn.group == group and defn.name == name:
            return defn
    return None
