import sqlparse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def load_db_dump(db_session: AsyncSession, dump: str):
    errors = []

    dump_statements = sqlparse.split(dump)

    for stmt in dump_statements:
        if not stmt.strip():
            continue

        try:
            await db_session.execute(text(stmt))
        except Exception as e:
            errors.append(e)

    return errors
