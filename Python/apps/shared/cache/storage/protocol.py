from typing import Protocol


class CacheStorage(Protocol):
    """Where the cached values are kept."""

    async def get(self, key: str) -> str | None:
        """Return the raw value of a key, or None when it is not there."""
        ...

    async def set(self, key: str, value: str, *, ttl: int | None = None) -> None:  # noqa: A003
        """Store a raw value under a key for the given number of seconds."""
        ...

    async def delete_prefix(self, prefix: str) -> int:
        """Remove every key starting with the prefix, return how many."""
        ...
