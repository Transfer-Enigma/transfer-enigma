from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette import status

from backend_user.api.v2.routes.post import _apply_demo_transforms, _normalize_routes
from backend_user.dependencies.auth_context import AuthContext, get_auth_context
from backend_user.services.route_link import (
    RouteLinkNotFoundError,
    get_route_by_link,
    parse_link_ids,
)
from module_shared.models.route import RouteResult

router = APIRouter(prefix="/v2/routes", tags=["v2", "routes"])


@router.get("/detail", response_model=RouteResult)
async def route_detail(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    segments: Annotated[str, Query()],
    included_services: Annotated[str | None, Query(alias="included-services")] = None,
):
    # get_auth_context falls through to a non-demo context for unknown UIDs
    # without raising, so an invalid demo link must explicitly become a 404.
    if request.headers.get("X-Demo-User-UID") and not auth.is_demo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        segment_ids = parse_link_ids(segments)
        service_ids = parse_link_ids(included_services)
    except RouteLinkNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    try:
        route = await get_route_by_link(segment_ids, service_ids)
    except RouteLinkNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    formatted = _normalize_routes([route])
    await _apply_demo_transforms(formatted, auth)
    segs, drop, may_be_invalid, services = formatted[0]
    return RouteResult(
        segments=segs,
        drop=drop,
        may_be_invalid=may_be_invalid,
        services=services,
    )
