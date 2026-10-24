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
    """Cache access for a single entity, driven by its cache policy.

    An entity without an enabled policy is never cached: reading it always
    misses and writing it does nothing.

    Keys are built as ``[source:]entity:parts`` where ``source`` is taken
    from the policy. For single-source entities (source is None) the key
    starts with the entity name itself.
    """

    def __init__(
        self,
        storage: CacheStorage,
        entity: CacheEntity,
        policies: Mapping[CacheEntity, CachePolicy] | None = None,
    ) -> None:
        self._storage = storage
        self._entity = entity
        self._policies = dict(policies or {})

    @property
    def entity(self) -> CacheEntity:
        return self._entity

    def policy(self) -> CachePolicy | None:
        return self._policies.get(self._entity)

    def is_enabled(self) -> bool:
        policy = self.policy()
        return policy is not None and policy.enabled

    def ttl(self) -> int | None:
        """TTL of the entity, or None when it must not be cached."""
        policy = self.policy()
        if policy is None or not policy.enabled:
            return None
        return policy.ttl

    def _source_prefix(self) -> str:
        policy = self.policy()
        if policy is not None and policy.source is not None:
            return policy.source
        return self._entity.value

    def key(self, *parts: str) -> str:
        """Build the storage key: ``[source:]entity:parts``."""
        policy = self.policy()
        if policy is not None and policy.source is not None:
            return ":".join((policy.source, self._entity.value, *parts))
        return ":".join((self._entity.value, *parts))

    async def get(
        self,
        *parts: str,
        model: type[BaseModel] | None = None,
        many: bool = True,
    ):
        """Read a cached value, validating it against the model when given."""
        if not self.is_enabled():
            return None

        key = self.key(*parts)
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
        *parts: str,
        data,
        ttl: int | None = None,
        dump: bool = False,
    ) -> bool:
        """Write a value, unless the entity is not cached."""
        policy_ttl = self.ttl()
        if policy_ttl is None:
            return False

        key = self.key(*parts)
        try:
            await self._storage.set(key, json.dumps(_prepare(data, dump=dump)), ttl=ttl or policy_ttl)
            return True
        except Exception:
            logger.exception("Failed to set cache for %s", key)
        return False

    @LocalLocker.locked(key=lambda self, *parts, **__: self.key(*parts))
    def set_async(
        self,
        *parts: str,
        data,
        ttl: int | None = None,
        dump: bool = False,
    ):
        """Write a value in the background, without waiting for the storage."""
        return asyncio.create_task(self.set(*parts, data=data, ttl=ttl, dump=dump))

    def silent_set_async(
        self,
        *parts: str,
        data,
        ttl: int | None = None,
        dump: bool = False,
    ):
        """Write a value in the background, ignoring a write already running."""
        with suppress(TaskAlreadyRunningError):
            return self.set_async(*parts, data=data, ttl=ttl, dump=dump)

    async def delete(self, *parts: str) -> None:
        """Remove a single cached value."""
        await self._storage.delete(self.key(*parts))

    async def flush(self) -> int:
        """Remove every cached value of this entity, return how many."""
        return await self._storage.delete_prefix(f"{self._source_prefix()}:")

    async def keys(self, *, limit: int = 100) -> list[str]:
        """List the cached keys of this entity."""
        return await self._storage.keys(f"{self._source_prefix()}:", limit=limit)
