import enum
import json
from dataclasses import dataclass, field
from typing import Any


class SettingType(enum.Enum):
    BOOL = "BOOL"
    INT = "INT"
    FLOAT = "FLOAT"
    STRING = "STRING"
    JSON = "JSON"


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
        return str(self.true_type_default)
