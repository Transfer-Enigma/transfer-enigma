from typing import Annotated

from fastapi import APIRouter, Depends

from backend_user.dependencies.auth_context import AuthContext, get_auth_context
from backend_user.schemas.form_requests import CalculateFormRequest
from backend_user.schemas.routes import NormalizedRoutes, RoutesDataResponse
from backend_user.services.profit import apply_demo_profit_to_routes
from backend_user.services.route_calculation import _strip_demo_fields, calculate_routes
from module_shared.models.route import Route

router = APIRouter(prefix="/v2/routes", tags=["v2", "routes"])


def _normalize_routes(routes: list[Route]) -> NormalizedRoutes:
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

    _strip_demo_fields(routes)


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
