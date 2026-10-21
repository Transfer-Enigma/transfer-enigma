import time
from typing import Protocol

from shared.redis_client import get_redis


class CacheStorage(Protocol):
    """Where the cached values are kept."""

    async def get(self, key: str) -> str | None:
        """Return the raw value of a key, or None when it is not there."""
        ...

    async def set(self, key: str, value: str, *, ttl: int) -> None:  # noqa: A003
        """Store a raw value under a key for the given number of seconds."""
        ...

    async def delete(self, key: str) -> None:
        """Remove a single key."""
        ...

    async def delete_prefix(self, prefix: str) -> int:
        """Remove every key starting with the prefix, return how many."""
        ...

    async def keys(self, prefix: str, *, limit: int = 100) -> list[str]:
        """List the keys starting with the prefix."""
        ...


class RedisStorage:
    """Storage backed by Redis."""

    async def get(self, key: str) -> str | None:
        return await get_redis().get(key)

    async def set(self, key: str, value: str, *, ttl: int) -> None:  # noqa: A003
        await get_redis().set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        await get_redis().delete(key)

    async def delete_prefix(self, prefix: str) -> int:
        deleted = 0
        async for key in get_redis().scan_iter(match=f"{prefix}*", count=100):
            await get_redis().delete(key)
            deleted += 1
        return deleted

    async def keys(self, prefix: str, *, limit: int = 100) -> list[str]:
        found: list[str] = []
        async for key in get_redis().scan_iter(match=f"{prefix}*", count=100):
            found.append(key)
            if len(found) >= limit:
                break
        return found


class LocalStorage:
    """Storage kept in the memory of the process.

    Useful for tests and for runs that must not depend on Redis.
    """

    def __init__(self) -> None:
        self._values: dict[str, tuple[str, float | None]] = {}

    async def get(self, key: str) -> str | None:
        entry = self._values.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and expires_at <= time.monotonic():
            del self._values[key]
            return None
        return value

    async def set(self, key: str, value: str, *, ttl: int) -> None:  # noqa: A003
        self._values[key] = (value, time.monotonic() + ttl)

    async def delete(self, key: str) -> None:
        self._values.pop(key, None)

    async def delete_prefix(self, prefix: str) -> int:
        keys = [key for key in self._values if key.startswith(prefix)]
        for key in keys:
            del self._values[key]
        return len(keys)

    async def keys(self, prefix: str, *, limit: int = 100) -> list[str]:
        found = [key for key in self._values if key.startswith(prefix)]
        return found[:limit]
