import json

from module_shared.schemas.setting import SettingModel, SettingType
from pydantic import BaseModel, field_validator


def parse_setting_value(  # noqa: C901
    value: str | None, value_type: SettingType | None
) -> bool | int | float | str | dict | list | None:
    """Parse and validate a string value according to SettingType.

    Returns the parsed typed value.
    Raises ValueError / json.JSONDecodeError if parsing fails.
    """
    if value is None:
        return None
    if value_type == SettingType.INT:
        return int(value)
    if value_type == SettingType.FLOAT:
        return float(value)
    if value_type == SettingType.BOOL:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value = value.lower()
            if value in ("true", "1"):
                return True
            if value in ("false", "0"):
                return False
        raise ValueError(f"Invalid 'value' \"{value}\" for 'value_type' \"{value_type}\"")
    if value_type == SettingType.JSON:
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value)
    return value


class SettingItem(BaseModel):
    group: str
    name: str
    value_type: SettingType
    value: bool | int | float | str | dict | list | None = None
    locked: bool = False

    @field_validator("value", mode="before")
    @classmethod
    def _parse_value(cls, v, info):
        return parse_setting_value(v, info.data.get("value_type"))

    @classmethod
    def from_model(cls, model: SettingModel) -> SettingItem:
        return cls(
            group=model.group,
            name=model.name,
            value_type=model.value_type,
            value=model.value,
            locked=model.locked,
        )
