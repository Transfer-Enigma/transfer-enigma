from shared.orm.cache_policy import CachePolicyModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def list_policies(session: AsyncSession) -> list[CachePolicyModel]:
    """All the cache policies."""
    result = await session.execute(select(CachePolicyModel))
    return list(result.scalars().all())


async def get_policy(session: AsyncSession, source: str, entity: str) -> CachePolicyModel | None:
    """The policy of an entity of a source, or None when it does not exist."""
    result = await session.execute(
        select(CachePolicyModel).where(
            CachePolicyModel.source == source,
            CachePolicyModel.entity == entity,
        ),
    )
    return result.scalar_one_or_none()


async def save_policy(
    session: AsyncSession,
    source: str,
    entity: str,
    *,
    enabled: bool,
    ttl: int,
) -> CachePolicyModel:
    """Store the policy of an entity of a source, creating it when needed."""
    model = await get_policy(session, source, entity)
    if model is None:
        model = CachePolicyModel(source=source, entity=entity, enabled=enabled, ttl=ttl)
        session.add(model)
    else:
        model.enabled = enabled
        model.ttl = ttl
    await session.flush()
    return model


async def delete_policies(session: AsyncSession, source: str) -> int:
    """Remove the policies of a source, return how many."""
    result = await session.execute(
        select(CachePolicyModel).where(CachePolicyModel.source == source),
    )
    models = list(result.scalars().all())
    for model in models:
        await session.delete(model)
    await session.flush()
    return len(models)
