from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from data.cache.registry import get_cache_registry
from entrypoints.admin.dependencies.auth import request_auth
from entrypoints.admin.schemas.data_browser import (
    CachePolicyCreate,
    CachePolicyPatch,
    CachePolicyResponse,
)
from entrypoints.admin.service.crud_cache_policies import crud_cache_policies
from shared.cache import CacheEntity
from shared.database import Database, get_database

router = APIRouter(prefix="/admin/api/cache/policies", tags=["cache-policies"])


@router.get("", response_model=list[CachePolicyResponse])
async def list_cache_policies(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
    source: str = Query("", description="Filter by source"),
    entity: str = Query("", description="Filter by entity"),
):
    async with db.session_context() as session:
        return await crud_cache_policies.list(session, source=source, entity=entity)


@router.get("/{policy_id}", response_model=CachePolicyResponse)
async def get_cache_policy(
    policy_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_cache_policies.get(session, policy_id)


@router.post("", response_model=CachePolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_cache_policy(
    payload: CachePolicyCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        result = await crud_cache_policies.create(session, payload)
    await get_cache_registry().load()
    return result


@router.patch("/{policy_id}", response_model=CachePolicyResponse)
async def update_cache_policy(
    policy_id: int,
    payload: CachePolicyPatch,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        result = await crud_cache_policies.patch(session, policy_id, payload)
    await get_cache_registry().load()
    return result


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cache_policy(
    policy_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        await crud_cache_policies.delete(session, policy_id)
    await get_cache_registry().load()


@router.post("/invalidate/{entity}", status_code=status.HTTP_204_NO_CONTENT)
async def invalidate_cache_policies_entity(
    entity: Annotated[str, Path(description="Cache entity to invalidate")],
):
    await get_cache_registry().invalidate_policies(CacheEntity(entity))


@router.post("/invalidate", status_code=status.HTTP_204_NO_CONTENT)
async def reload_cache_policies():
    """Re-read all cache policies from the database and clear the local policy cache."""
    await get_cache_registry().load()
