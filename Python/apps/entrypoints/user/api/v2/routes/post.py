from typing import Annotated

from fastapi import APIRouter, Depends

from entrypoints.user.dependencies.auth_context import bind_caller_context
from entrypoints.user.schemas.form_requests import CalculateFormRequest
from entrypoints.user.schemas.routes import NormalizedRoutes, RoutesDataResponse
from services.demo_transforms import apply_demo_transforms
from services.route_calculation import calculate_routes
from shared.context import CallerContext
from shared.dto.route import RouteResult

router = APIRouter(prefix="/v2/routes", tags=["v2", "routes"])


def _normalize_routes(routes: list[RouteResult]) -> NormalizedRoutes:
    return [(r.segments, r.drop, r.may_be_invalid, r.services) for r in routes]


@router.post("/calculate", response_model=RoutesDataResponse)
async def calculate(
    request: CalculateFormRequest,
    context: Annotated[CallerContext, Depends(bind_caller_context)],
):
    routes, errors = await calculate_routes(request)
    for route in routes:
        await apply_demo_transforms(route)
    formatted = _normalize_routes(routes)

    return {
        "errors": errors,
        "routes": formatted,
    }
