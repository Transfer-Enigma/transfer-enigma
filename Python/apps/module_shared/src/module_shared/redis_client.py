import logging
from functools import cache

import redis.asyncio as aioredis
from module_shared.config import get_settings

logger = logging.getLogger(__name__)


class RedisClient:
    _client: aioredis.Redis | None = None

    async def init(self):
        settings = get_settings()
        self._client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )
        logger.info(
            "Redis client created: %s:%d/%d",
            settings.REDIS_HOST,
            settings.REDIS_PORT,
            settings.REDIS_DB,
        )

    async def close(self):
        if self._client is not None:
            await self._client.close()
            self._client = None
            logger.info("Redis client closed")

    @property
    def client(self) -> aioredis.Redis:
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call init() first.")
        return self._client


@cache
def get_redis_client() -> RedisClient:
    return RedisClient()


def get_redis() -> aioredis.Redis:
    return get_redis_client().client
