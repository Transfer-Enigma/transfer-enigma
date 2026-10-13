import asyncio
import json
from collections.abc import Iterable
from contextlib import suppress
from logging import Logger

from module_shared.redis_client import get_redis
from module_shared.repositories.locker import TaskAlreadyRunningError
from module_shared.repositories.locker.local_locker import LocalLocker
from pydantic import BaseModel


class CacheController:
    def __init__(self, logger: Logger):
        self._logger = logger

    async def get_cached(self, cache_key: str, pydantic_class: type[BaseModel] | None = None, iterable: bool = True):
        try:
            redis = get_redis()
            cached = await redis.get(cache_key)
            if cached is not None:
                raw_data = json.loads(cached)
                if not pydantic_class:
                    return raw_data

                try:
                    return (
                        [pydantic_class.model_validate(r) for r in raw_data]
                        if iterable else
                        pydantic_class.model_validate(raw_data)
                    )
                except Exception:
                    self._logger.warning("Corrupt cache data for %s, re-fetching", cache_key, exc_info=True)
        except Exception:
            self._logger.warning("Redis unavailable for %s, falling back to API", cache_key, exc_info=True)

    async def set_cache(self, key: str, data, ttl: int, model_dump: bool = False) -> bool:
        try:
            redis = get_redis()

            if isinstance(data, BaseModel):
                prepared_data = data.model_dump(mode="json")
            elif isinstance(data, Iterable):
                prepared_data = [r.model_dump(mode="json") for r in data] if model_dump else data
            else:
                prepared_data = data.model_dump(mode="json") if model_dump else data

            await redis.set(key, json.dumps(prepared_data), ex=ttl)
            return True
        except Exception:
            self._logger.exception("Failed to set cache for %s", key)

        return False

    @LocalLocker.locked(key=lambda key, *_, **__: key)
    def set_cache_async(self, key: str, data, ttl: int, model_dump: bool = False):
        return asyncio.create_task(self.set_cache(key, data, ttl, model_dump))

    def silent_set_cache_async(self, key: str, data, ttl: int, model_dump: bool = False):
        with suppress(TaskAlreadyRunningError):
            return self.set_cache_async(key, data, ttl, model_dump)
