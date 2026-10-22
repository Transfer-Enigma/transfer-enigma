from shared.database import get_database
from shared.orm.container import ContainerModel
from sqlalchemy import select


async def get_containers() -> list[ContainerModel]:
    """All the containers of the database, the smallest one first."""
    async with get_database().session_context() as session:
        result = await session.execute(select(ContainerModel).order_by(ContainerModel.size))
        return list(result.scalars().all())
