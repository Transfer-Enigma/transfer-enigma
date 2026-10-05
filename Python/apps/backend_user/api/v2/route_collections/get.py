from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette import status

from backend_user.api.v2.routes.post import _apply_demo_transforms, _normalize_routes
from backend_user.dependencies.auth_context import AuthContext, get_auth_context
from backend_user.schemas.route_collections import CollectionResponse
from backend_user.services import route_collection
from backend_user.services.route_link import RouteLinkNotFoundError
from module_shared.models.route import RouteResult

router = APIRouter(prefix="/v2/collections", tags=["v2", "collections"])


@router.get("/{uid}", response_model=CollectionResponse)
async def get_collection_endpoint(
    uid: str,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
):
    collection = await route_collection.get_collection(uid)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Demo access is only allowed for the owning demo. Collections
    # created outside of demo are never available via demo links.
    if request.headers.get("X-Demo-User-UID") and (not auth.is_demo or auth.demo_uid != collection.demo_uid):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        routes = await route_collection.resolve_collection(collection)
    except RouteLinkNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    formatted = _normalize_routes(routes)
    await _apply_demo_transforms(formatted, auth)
    return {
        "uid": collection.uid,
        "routes": [
            RouteResult(segments=segments, drop=drop, may_be_invalid=may_be_invalid, services=services)
            for segments, drop, may_be_invalid, services in formatted
        ],
    }
