from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent

from entrypoints.user.dependencies.auth_context import AuthContext, get_auth_context
from entrypoints.user.schemas.form_requests import CalculateFormRequest
from services.demo.transforms import apply_demo_transforms_to_route
from services.routes.calculation import calculate_routes_stream
from shared.models.route_entities import RouteResult

router = APIRouter(prefix="/v3/routes", tags=["v3", "routes"])


async def _sse_generator(
    request: CalculateFormRequest,
    auth: AuthContext,
    last_event_id: int | None = None,
) -> AsyncGenerator[ServerSentEvent]:
    current_id = last_event_id + 1 if last_event_id is not None else 0

    async for item in calculate_routes_stream(request):
        if isinstance(item, RouteResult):
            await apply_demo_transforms_to_route(item, auth)

        event_type = "route" if isinstance(item, RouteResult) else "error"
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
        "| `route` | A single calculated route (`RouteResult`) |\n"
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
) -> AsyncGenerator[ServerSentEvent]:
    if response is not None:
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"

    async for event in _sse_generator(request, auth, last_event_id):
        yield event
