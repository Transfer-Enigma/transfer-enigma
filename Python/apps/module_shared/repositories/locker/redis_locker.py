from typing import Any, TypeVar

from . import Locker, TaskAlreadyRunningError

T = TypeVar("T")


class RedisLocker(Locker):
    _redis: Any = None
    _default_ttl: int = 30  # TTL for tasks acquiring

    @classmethod
    def acquire(cls, key: str) -> None:
        raise RuntimeError("Sync methods are unsupported in this context")

    @classmethod
    def release(cls, key: str) -> None:
        raise RuntimeError("Sync methods are unsupported in this context")

    @classmethod
    def is_running(cls, key: str) -> bool:
        raise RuntimeError("Sync methods are unsupported in this context")

    @classmethod
    def _get_key(cls, key: str):
        return f"locked:{key}"

    @classmethod
    def init(cls, redis_client: Any, default_ttl: int = 10) -> None:
        cls._redis = redis_client
        cls._default_ttl = default_ttl

    @classmethod
    def _check_initialized(cls) -> None:
        if cls._redis is None:
            raise RuntimeError("RedisLocker does not initialized. Call 'RedisLocker.init'")

    @classmethod
    async def aacquire(cls, key: str) -> None:
        cls._check_initialized()

        # SET NX EX - Atomic Operation: set if not exists
        acquired = await cls._redis.set(cls._get_key(key), "1", nx=True, ex=cls._default_ttl)

        if not acquired:
            raise TaskAlreadyRunningError(key)

    @classmethod
    async def arelease(cls, key: str) -> None:
        cls._check_initialized()
        await cls._redis.delete(cls._get_key(key))

    @classmethod
    async def ais_running(cls, key: str) -> bool:
        cls._check_initialized()
        return bool(await cls._redis.exists(cls._get_key(key)))
