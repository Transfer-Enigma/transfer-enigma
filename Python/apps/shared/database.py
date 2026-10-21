from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import cache
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    __table_args__: dict[str, Any] | tuple[Any] = {
        "mysql_default_charset": settings.DB_CHARSET,
        "mysql_collate": settings.DB_COLLATE,
    }


def _build_db_url():
    scheme = settings.DB_SCHEME
    user = settings.DB_USER
    password = settings.DB_PASS
    host = settings.DB_HOST
    port = settings.DB_PORT
    name = settings.DB_NAME

    return f"{scheme}://{user}:{password}@{host}:{port}/{name}"


class Database:
    _engine: AsyncEngine = None
    _sessionmaker: async_sessionmaker | None = None

    async def init(self):
        db_url = _build_db_url()
        self._engine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
        )
        self._sessionmaker = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def close(self):
        await self._engine.dispose(True)

    async def session(self) -> AsyncGenerator:
        if not self._sessionmaker:
            await self.init()

        if not self._sessionmaker:
            raise Exception("No sessionmaker")

        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    session_context = asynccontextmanager(session)


@cache
def get_database():
    return Database()
