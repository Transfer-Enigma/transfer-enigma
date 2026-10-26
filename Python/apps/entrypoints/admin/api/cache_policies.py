from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from data.cache.registry import get_cache_registry
from entrypoints.admin.dependencies.auth import request_auth
from entrypoints.admin.schemas.data_browser import (
    CacheEntriesResponse,
    CacheEntryItem,
    CacheInvalidateResponse,
    CachePolicyCreate,
    CachePolicyPatch,
    CachePolicyResponse,
)
from entrypoints.admin.service.crud_cache_policies import crud_cache_policies
from shared.cache import CacheEntity, RedisStorage, cache_prefix, flush_cache
from shared.database import Database, get_database

router = APIRouter(prefix="/cache/policies", tags=["cache-policies"])


@router.get("", response_model=list[CachePolicyResponse])
async def list_cache_policies(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
    source: str | None = Query(None, description="Filter by source"),
    entity: str | None = Query(None, description="Filter by entity"),
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


@router.get("/{policy_id}/entries", response_model=CacheEntriesResponse)
async def list_cache_policy_entries(
    policy_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
):
    """Show what a policy has stored right now, up to ``limit`` values."""
    async with db.session_context() as session:
        policy = await crud_cache_policies.get(session, policy_id)

    try:
        entity = CacheEntity(policy.entity)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown cache entity {policy.entity!r}",
        ) from exc

    backend = get_cache_registry().backend(entity, source=policy.source)
    entries = await backend.entries(limit=limit)
    return CacheEntriesResponse(
        policy_id=policy_id,
        prefix=cache_prefix(entity, policy.source),
        count=len(entries),
        entries=[CacheEntryItem(key=key, value=value) for key, value in entries],
    )


@router.post("", response_model=CachePolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_cache_policy(
    payload: CachePolicyCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        result = await crud_cache_policies.create(session, payload)

    await flush_cache(RedisStorage(), CacheEntity(result.entity), result.source)
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
        policy = await crud_cache_policies.get(session, policy_id)
        await flush_cache(RedisStorage(), CacheEntity(policy.entity), policy.source)
        await crud_cache_policies.delete(session, policy_id)

    await get_cache_registry().load()


@router.post("/invalidate", response_model=CacheInvalidateResponse)
async def invalidate_all_cache(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    """Remove every cached value of every configured policy."""
    async with db.session_context() as session:
        policies = await crud_cache_policies.list(session, source="", entity="")

    storage = RedisStorage()
    deleted = 0
    for policy in policies:
        deleted += await flush_cache(storage, CacheEntity(policy.entity), policy.source)
    return CacheInvalidateResponse(deleted=deleted)


@router.post("/{policy_id}/invalidate", response_model=CacheInvalidateResponse)
async def invalidate_cache_policy(
    policy_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    """Remove every cached value of a single policy."""
    async with db.session_context() as session:
        policy = await crud_cache_policies.get(session, policy_id)

    deleted = await flush_cache(RedisStorage(), CacheEntity(policy.entity), policy.source)
    return CacheInvalidateResponse(deleted=deleted)
