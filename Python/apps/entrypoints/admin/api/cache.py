from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from entrypoints.admin.dependencies.auth_context import bind_caller_context
from pydantic import BaseModel, Field
from services.cache_management import (
    flush_source,
    list_keys,
    list_sources,
    remove_source,
    update_policy,
)
from shared.cache import CacheEntity
from shared.context import CallerContext

router = APIRouter(prefix="/cache", tags=["cache"])


class CachePolicyPayload(BaseModel):
    enabled: bool = True
    ttl: int = Field(gt=0, description="The time to live of the cached values, in seconds")


@router.get("")
async def cache_sources(_: Annotated[CallerContext, Depends(bind_caller_context)]):
    """The sources of the cache, with the policy of every entity."""
    return {"sources": await list_sources()}


@router.get("/{source}")
async def cache_keys(
    source: str,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    entity: str | None = None,
    limit: int = 100,
):
    """The cached keys of a source, or of one of its entities."""
    if entity is not None and entity not in CacheEntity.__members__.values():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown entity '{entity}'")

    return {"source": source, "keys": await list_keys(source, entity, limit)}


@router.patch("/{source}/{entity}")
async def change_cache_policy(
    source: str,
    entity: str,
    payload: CachePolicyPayload,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    """Change the policy of an entity of a source."""
    if entity not in CacheEntity.__members__.values():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown entity '{entity}'")

    await update_policy(source, entity, enabled=payload.enabled, ttl=payload.ttl)
    return {"source": source, "entity": entity, "enabled": payload.enabled, "ttl": payload.ttl}


@router.delete("/{source}")
async def clear_cache_source(
    source: str,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    """Remove the cached values of a source."""
    return {"source": source, "removed": await flush_source(source)}


@router.delete("/{source}/policies")
async def remove_cache_source(
    source: str,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    """Remove the policies of a source and its cached values."""
    return {"source": source, "removed": await remove_source(source)}
