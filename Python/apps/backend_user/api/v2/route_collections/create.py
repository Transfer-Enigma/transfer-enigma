from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from backend_user.dependencies.auth_context import AuthContext, get_auth_context
from backend_user.schemas.route_collections import (
    CreateCollectionRequest,
    CreatedCollectionResponse,
)
from backend_user.services import route_collection
from backend_user.services.route_link import RouteLinkNotFoundError

router = APIRouter(prefix="/v2/collections", tags=["v2", "collections"])


@router.post("", response_model=CreatedCollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection_endpoint(
    request: CreateCollectionRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
):
    try:
        model = await route_collection.create_collection(
            request.items, auth.demo_uid if auth.is_demo else None
        )
    except RouteLinkNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return {"uid": model.uid}
