from typing import Annotated

from fastapi import APIRouter, Depends

from entrypoints.user.dependencies.auth_context import AuthContext, get_auth_context
from entrypoints.user.schemas.form_requests import CalculateFormRequest
from entrypoints.user.schemas.routes import NormalizedRoutes, RoutesDataResponse
from services.profit import apply_demo_profit_to_routes
from services.route_calculation import _strip_demo_fields, calculate_routes
from shared.cache_settings import get_setting_cached
from shared.dto.route import RouteResult

router = APIRouter(prefix="/v2/routes", tags=["v2", "routes"])


def _normalize_routes(routes: list[RouteResult]) -> NormalizedRoutes:
    return [(r.segments, r.drop, r.may_be_invalid, r.services) for r in routes]


async def _apply_demo_transforms(routes: NormalizedRoutes, auth: AuthContext) -> None:
    if not auth.is_demo:
        return

    if auth.sea_profit or auth.rail_profit:
        await apply_demo_profit_to_routes(
            routes,
            auth.sea_profit,
            auth.sea_profit_currency,
            auth.rail_profit,
            auth.rail_profit_currency,
        )

    setting = await get_setting_cached("feature-flag", "demo-excluded-fields")
    excluded_fields = setting.value if setting and isinstance(setting.value, list) else []
    _strip_demo_fields(routes, excluded_fields)


@router.post("/calculate", response_model=RoutesDataResponse)
async def calculate(
    request: CalculateFormRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
):
    routes, errors = await calculate_routes(request)
    formatted = _normalize_routes(routes)
    await _apply_demo_transforms(formatted, auth)

    return {
        "errors": errors,
        "routes": formatted,
    }
