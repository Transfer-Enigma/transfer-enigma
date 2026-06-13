from backend_admin.schemas.data_browser import PointCreate, PointPatch, PointResponse
from backend_admin.service.crud_base import CRUDBase, FilterDef
from module_data_internal.schemas import PointModel


class CRUDPoint(CRUDBase):
    model = PointModel
    create_schema = PointCreate
    update_schema = PointCreate
    patch_schema = PointPatch
    response_schema = PointResponse
    list_filters = [
        FilterDef("city", "city", "like"),
        FilterDef("country", "country", "like"),
    ]

    def _build_instance(self, data: PointCreate) -> PointModel:
        return PointModel(
            city=data.city.strip(),
            country=data.country.strip(),
            RU_city=data.RU_city.strip() if data.RU_city else None,
            RU_country=data.RU_country.strip() if data.RU_country else None,
        )

    def _apply_update(self, model: PointModel, data: PointCreate) -> None:
        model.city = data.city.strip()
        model.country = data.country.strip()
        model.RU_city = data.RU_city.strip() if data.RU_city else None
        model.RU_country = data.RU_country.strip() if data.RU_country else None

    def _apply_patch(self, model: PointModel, data: PointPatch) -> None:
        if data.city is not None:
            model.city = data.city.strip()
        if data.country is not None:
            model.country = data.country.strip()
        if data.RU_city is not None:
            model.RU_city = data.RU_city.strip() if data.RU_city else None
        if data.RU_country is not None:
            model.RU_country = data.RU_country.strip() if data.RU_country else None


crud_points = CRUDPoint()
