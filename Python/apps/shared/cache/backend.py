import asyncio
import json
import logging
from collections.abc import Iterable, Mapping
from contextlib import suppress

from pydantic import BaseModel
from shared.concurrency import TaskAlreadyRunningError
from shared.concurrency.local_locker import LocalLocker

from .entity import CacheEntity
from .policy import CachePolicy
from .storage.protocol import CacheStorage

logger = logging.getLogger(__name__)


def _prepare(data, *, dump: bool):
    """Turn the value into something that can be serialized to JSON."""
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, (str, bytes, dict)):
        return data
    if isinstance(data, Iterable):
        if not dump:
            return data
        return [item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in data]
    return data


class CacheBackend:
    """Cache access over a pluggable storage, driven by the cache policies.

    An entity without an enabled policy is never cached: reading it always
    misses and writing it does nothing.
    """

    def __init__(
        self,
        storage: CacheStorage,
        source: str,
        policies: Mapping[CacheEntity, CachePolicy] | None = None,
    ) -> None:
        self._storage = storage
        self._source = source
        self._policies = dict(policies or {})

    @property
    def source(self) -> str:
        return self._source

    def key(self, entity: CacheEntity, *parts: str) -> str:
        """Build the storage key of an entity and its parts."""
        return ":".join((self._source, entity.value, *parts))

    def policy(self, entity: CacheEntity) -> CachePolicy | None:
        return self._policies.get(entity)

    def is_enabled(self, entity: CacheEntity) -> bool:
        policy = self._policies.get(entity)
        return policy is not None and policy.enabled

    def ttl(self, entity: CacheEntity) -> int | None:
        """TTL of an entity, or None when it must not be cached."""
        policy = self._policies.get(entity)
        if policy is None or not policy.enabled:
            return None
        return policy.ttl

    async def get(
        self,
        entity: CacheEntity,
        *parts: str,
        model: type[BaseModel] | None = None,
        many: bool = True,
    ):
        """Read a cached value, validating it against the model when given."""
        if not self.is_enabled(entity):
            return None

        key = self.key(entity, *parts)
        try:
            raw = await self._storage.get(key)
        except Exception:
            logger.warning("Cache storage unavailable for %s, falling back to the source", key, exc_info=True)
            return None

        if raw is None:
            return None

        return self._deserialize(raw, key, model, many)

    def _deserialize(self, raw: str, key: str, model: type[BaseModel] | None, many: bool):
        """Turn the stored value back into the data it holds."""
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            logger.warning("Corrupt cache data for %s, re-fetching", key, exc_info=True)
            return None

        if model is None:
            return data

        try:
            if many:
                return [model.model_validate(item) for item in data]
            return model.model_validate(data)
        except Exception:
            logger.warning("Corrupt cache data for %s, re-fetching", key, exc_info=True)
            return None

    async def set(  # noqa: A003
        self,
        entity: CacheEntity,
        *parts: str,
        data,
        ttl: int | None = None,
        dump: bool = False,
    ) -> bool:
        """Write a value, unless the entity is not cached."""
        policy_ttl = self.ttl(entity)
        if policy_ttl is None:
            return False

        key = self.key(entity, *parts)
        try:
            await self._storage.set(key, json.dumps(_prepare(data, dump=dump)), ttl=ttl or policy_ttl)
            return True
        except Exception:
            logger.exception("Failed to set cache for %s", key)
        return False

    @LocalLocker.locked(key=lambda self, entity, *parts, **__: self.key(entity, *parts))
    def set_async(
        self,
        entity: CacheEntity,
        *parts: str,
        data,
        ttl: int | None = None,
        dump: bool = False,
    ):
        """Write a value in the background, without waiting for the storage."""
        return asyncio.create_task(self.set(entity, *parts, data=data, ttl=ttl, dump=dump))

    def silent_set_async(
        self,
        entity: CacheEntity,
        *parts: str,
        data,
        ttl: int | None = None,
        dump: bool = False,
    ):
        """Write a value in the background, ignoring a write already running."""
        with suppress(TaskAlreadyRunningError):
            return self.set_async(entity, *parts, data=data, ttl=ttl, dump=dump)

    async def delete(self, entity: CacheEntity, *parts: str) -> None:
        """Remove a single cached value."""
        await self._storage.delete(self.key(entity, *parts))

    async def flush(self) -> int:
        """Remove every cached value of the source, return how many."""
        return await self._storage.delete_prefix(f"{self._source}:")

    async def keys(self, entity: CacheEntity | None = None, *, limit: int = 100) -> list[str]:
        """List the cached keys of the source, or of one of its entities."""
        prefix = f"{self._source}:" if entity is None else self.key(entity)
        return await self._storage.keys(prefix, limit=limit)
