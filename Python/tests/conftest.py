import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["ENVIRONMENT"] = "test"
os.environ["DISABLE_USER_AUTH_CHECK"] = "true"
os.environ["DB_SCHEME"] = "sqlite+aiosqlite"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "3306"
os.environ["DB_NAME"] = "test_db"
os.environ["DB_USER"] = "test_user"
os.environ["DB_PASS"] = "test_pass"
os.environ["ADMIN_LOGIN"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["AUTHJWT_SECRET_KEY"] = "test-secret-key"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["REFRESH_TOKEN_EXPIRE_MINUTES"] = "4320"
os.environ["FESCO_API_KEY"] = "test-key"
os.environ["DEFAULT_GSHEETS_URL"] = "https://sheets.example.com"
os.environ["DEFAULT_SEA_ROUTES_WS"] = "sea"
os.environ["DEFAULT_RAIL_ROUTES_WS"] = "rail"
os.environ["DEFAULT_TRUCK_ROUTES_WS"] = "truck"
os.environ["DEFAULT_DROPP_ROUTES_WS"] = "dropp"
os.environ["DEFAULT_POINTS_WS"] = "points"
os.environ["DEFAULT_SERVICES_WS"] = "services"

from module_shared.database import Base, Database  # noqa: E402


@pytest_asyncio.fixture
async def sqlite_db() -> AsyncGenerator[Database]:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db = Database()
    db._engine = engine
    db._sessionmaker = sessionmaker

    yield db

    await engine.dispose()


@pytest_asyncio.fixture
async def sqlite_session(sqlite_db: Database) -> AsyncGenerator[AsyncSession]:
    async with sqlite_db.session_context() as session:
        yield session
