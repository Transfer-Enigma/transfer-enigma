from typing import Annotated

from fastapi import APIRouter, Depends

from entrypoints.user.dependencies.auth_context import bind_caller_context
from entrypoints.user.schemas.form_requests import CalculateFormRequest
from entrypoints.user.schemas.routes import NormalizedRoutes, RoutesDataResponse
from services.profit import apply_demo_profit_to_routes
from services.route_calculation import _strip_demo_fields, calculate_routes
from shared.context import CallerContext, ContextKind
from shared.dto.route import RouteResult

router = APIRouter(prefix="/v2/routes", tags=["v2", "routes"])


def _normalize_routes(routes: list[RouteResult]) -> NormalizedRoutes:
    return [(r.segments, r.drop, r.may_be_invalid, r.services) for r in routes]


async def _apply_demo_transforms(routes: NormalizedRoutes, context: CallerContext) -> None:
    if context.kind != ContextKind.DEMO:
        return

    if context.sea_profit or context.rail_profit:
        await apply_demo_profit_to_routes(
            routes,
            context.sea_profit,
            context.sea_profit_currency,
            context.rail_profit,
            context.rail_profit_currency,
        )

    _strip_demo_fields(routes, context.excluded_fields)


@router.post("/calculate", response_model=RoutesDataResponse)
async def calculate(
    request: CalculateFormRequest,
    context: Annotated[CallerContext, Depends(bind_caller_context)],
):
    routes, errors = await calculate_routes(request)
    formatted = _normalize_routes(routes)
    await _apply_demo_transforms(formatted, context)

    return {
        "errors": errors,
        "routes": formatted,
    }
