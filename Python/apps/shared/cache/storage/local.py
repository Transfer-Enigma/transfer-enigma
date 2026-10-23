import time


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

    async def set(self, key: str, value: str, *, ttl: int | None = None) -> None:  # noqa: A003
        self._values[key] = (value, None if ttl is None else time.monotonic() + ttl)

    async def delete(self, key: str) -> None:
        self._values.pop(key, None)

    async def delete_prefix(self, prefix: str) -> int:
        keys = [key for key in self._values if key.startswith(prefix)]
        for key in keys:
            del self._values[key]
        return len(keys)
