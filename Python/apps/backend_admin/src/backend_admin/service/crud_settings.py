from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from backend_admin.schemas.data_browser import SettingCreate, SettingPatch, SettingResponse
from backend_admin.service.crud_base import CRUDBase, FilterDef
from module_shared.models.setting import parse_setting_value
from module_shared.schemas.setting import SettingModel, SettingType
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDSetting(CRUDBase):
    model = SettingModel
    create_schema = SettingCreate
    update_schema = SettingCreate
    patch_schema = SettingPatch
    response_schema = SettingResponse
    list_filters = [
        FilterDef("group", "group", "like"),
        FilterDef("q", "name", "like"),
    ]

    @staticmethod
    def _validate_value(value: str | None, value_type: SettingType | None) -> None:
        if value is None:
            return
        try:
            parse_setting_value(value.strip(), value_type)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Invalid value for type {value_type}: {exc}",
            ) from exc

    def _check_locked_update(self, model: SettingModel, data: SettingCreate) -> None:
        if not model.locked:
            return
        if model.group != data.group.strip() or model.name != data.name.strip():
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Cannot rename locked setting",
            )
        if model.value_type != data.value_type:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Cannot change type of locked setting",
            )

    def _check_locked_patch(self, model: SettingModel, data: SettingPatch) -> None:
        if not model.locked:
            return
        if data.group is not None and data.group.strip() != model.group:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Cannot rename locked setting",
            )
        if data.name is not None and data.name.strip() != model.name:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Cannot rename locked setting",
            )
        if data.value_type is not None and data.value_type != model.value_type:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Cannot change type of locked setting",
            )

    def _build_instance(self, data: SettingCreate) -> SettingModel:
        self._validate_value(data.value, data.value_type)
        return SettingModel(
            group=data.group.strip(),
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            value_type=data.value_type,
            value=data.value.strip() if data.value else None,
        )

    def _apply_update(self, model: SettingModel, data: SettingCreate) -> None:
        self._validate_value(data.value, data.value_type)
        model.group = data.group.strip()
        model.name = data.name.strip()
        model.description = data.description.strip() if data.description else None
        model.value_type = data.value_type
        model.value = data.value.strip() if data.value else None

    def _apply_patch(self, model: SettingModel, data: SettingPatch) -> None:
        if data.group is not None:
            model.group = data.group.strip()
        if data.name is not None:
            model.name = data.name.strip()
        if data.description is not None:
            model.description = data.description.strip() if data.description else None
        if data.value_type is not None:
            model.value_type = data.value_type
        if data.value is not None:
            model.value = data.value.strip() if data.value else None

    async def update(self, session: AsyncSession, id: int, data: SettingCreate) -> SettingResponse:  # noqa: A002
        model = await self._get_or_404(session, id)
        self._check_locked_update(model, data)
        self._apply_update(model, data)
        await session.flush()
        await session.refresh(model)
        return self.response_schema.from_model(model)

    async def patch(self, session: AsyncSession, id: int, data: SettingPatch) -> SettingResponse:  # noqa: A002
        model = await self._get_or_404(session, id)
        self._check_locked_patch(model, data)
        if data.value is not None:
            self._validate_value(data.value, data.value_type or model.value_type)
        self._apply_patch(model, data)
        await session.flush()
        await session.refresh(model)
        return self.response_schema.from_model(model)

    async def delete(self, session: AsyncSession, id: int) -> None:  # noqa: A002
        model = await self._get_or_404(session, id)
        if model.locked:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Cannot delete locked setting",
            )
        await session.delete(model)
        await session.flush()


crud_settings = CRUDSetting()
