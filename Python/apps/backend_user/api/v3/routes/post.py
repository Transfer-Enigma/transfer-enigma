from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent

from backend_user.dependencies.auth_context import AuthContext, get_auth_context
from backend_user.schemas.form_requests import CalculateFormRequest
from backend_user.services.profit import apply_demo_profit_to_route
from backend_user.services.route_calculation import calculate_routes_stream
from module_shared.config import get_settings as get_shared_settings
from module_shared.models.route import Route

router = APIRouter(prefix="/v3/routes", tags=["v3", "routes"])


async def _apply_demo_transforms_to_route(route: Route, auth: AuthContext) -> None:
    if auth.sea_profit or auth.rail_profit:
        await apply_demo_profit_to_route(
            route,
            auth.sea_profit,
            auth.sea_profit_currency,
            auth.rail_profit,
            auth.rail_profit_currency,
        )

    excluded_fields = get_shared_settings().DEMO_EXCLUDED_FIELDS
    for segment in route.segments:
        for field in excluded_fields:
            setattr(segment, field, None)


async def _sse_generator(
    request: CalculateFormRequest,
    auth: AuthContext,
    last_event_id: int | None = None,
) -> AsyncGenerator[ServerSentEvent, None]:
    current_id = last_event_id + 1 if last_event_id is not None else 0

    async for item in calculate_routes_stream(request):
        if isinstance(item, Route) and auth.is_demo:
            await _apply_demo_transforms_to_route(item, auth)

        event_type = "route" if isinstance(item, Route) else "error"
        yield ServerSentEvent(data=item, event=event_type, id=str(current_id))
        current_id += 1


@router.post(
    "/calculate",
    response_class=EventSourceResponse,
    summary="Calculate routes (SSE stream)",
    description=(
        "Progressive route calculation with Server-Sent Events.\n\n"
        "Each route or error is streamed as it becomes available, "
        "without waiting for all calculations to complete.\n\n"
        "## SSE Event Types\n\n"
        "| Event | Description |\n"
        "|-------|-------------|\n"
        "| `route` | A single calculated route (`Route`) |\n"
        "| `error` | A calculation error with type, text, and source |\n\n"
        "## SSE Format\n\n"
        "```\n"
        "id: 0\n"
        "event: route\n"
        "data: {\"segments\":[...],\"drop\":null,\"may_be_invalid\":false,\"services\":[]}\n"
        "\n"
        "id: 1\n"
        "event: error\n"
        "data: {\"error_type\":\"Exception\",\"error_text\":\"...\",\"source\":\"internal\"}\n"
        "```"
    ),
)
async def calculate_sse(
    request: CalculateFormRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    last_event_id: Annotated[int | None, Header()] = None,
    response: Response = None,
) -> AsyncGenerator[ServerSentEvent, None]:
    if response is not None:
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"

    async for event in _sse_generator(request, auth, last_event_id):
        yield event
