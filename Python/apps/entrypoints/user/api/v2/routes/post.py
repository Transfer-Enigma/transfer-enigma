from typing import Annotated

from fastapi import APIRouter, Depends

from entrypoints.user.dependencies.auth_context import AuthContext, get_auth_context
from entrypoints.user.schemas.form_requests import CalculateFormRequest
from entrypoints.user.schemas.routes import RoutesDataResponse, normalize_routes
from services.demo.transforms import apply_demo_transforms_to_route
from services.routes.calculation import calculate_routes

router = APIRouter(prefix="/v2/routes", tags=["v2", "routes"])


@router.post("/calculate", response_model=RoutesDataResponse)
async def calculate(
    request: CalculateFormRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
):
    routes, errors = await calculate_routes(request)

    for route in routes:
        await apply_demo_transforms_to_route(route, auth)

    return {
        "errors": errors,
        "routes": normalize_routes(routes),
    }
