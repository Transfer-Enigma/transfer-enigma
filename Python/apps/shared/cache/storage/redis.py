from shared.redis_client import get_redis


class RedisStorage:
    """Storage backed by Redis."""

    async def get(self, key: str) -> str | None:
        return await get_redis().get(key)

    async def set(self, key: str, value: str, *, ttl: int | None = None) -> None:  # noqa: A003
        await get_redis().set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        await get_redis().delete(key)

    async def delete_prefix(self, prefix: str) -> int:
        deleted = 0
        async for key in get_redis().scan_iter(match=f"{prefix}*", count=100):
            await get_redis().delete(key)
            deleted += 1
        return deleted

    async def keys(self, prefix: str, limit: int) -> list[str]:
        found: list[str] = []
        async for key in get_redis().scan_iter(match=f"{prefix}*", count=100):
            found.append(key)
            if len(found) >= limit:
                break
        return found
