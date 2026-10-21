import datetime

from shared.database import get_database
<<<<<<< HEAD
from shared.orm.container import ContainerModel
=======
from shared.schemas.container import ContainerModel
>>>>>>> a90e866f (Python: Rename packages by architecture layer)
from sqlalchemy import select

from .transformers.containers import transform_containers


async def get_containers(date: datetime.date, departure_id: str, destination_id: str):
    async with get_database().session_context() as session:
        res = await session.execute(
            select(ContainerModel).order_by(ContainerModel.size)
        )
    orm_containers = res.scalars().all()
    return transform_containers(orm_containers)


def search_container_ids(containers: list, weight: int, size: int):
    return [
        c.id
        for c in containers
        if c.size == size
        and c.weight_from <= weight <= c.weight_to
    ]
