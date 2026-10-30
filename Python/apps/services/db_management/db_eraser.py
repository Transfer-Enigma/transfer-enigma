from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TABLES = {"drop", "service_prices", "prices", "routes", "companies", "containers", "points", "services"}


async def clear_database_data(session: AsyncSession):
    await session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

    for table in TABLES:
        await session.execute(text(f"DELETE FROM `{table}`"))

    await session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
