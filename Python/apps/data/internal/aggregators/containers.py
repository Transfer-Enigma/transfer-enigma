import datetime

from data.repositories.containers import get_containers as load_containers
from shared.dto.route import ContainerItem

from .transformers.containers import transform_containers


async def get_containers(date: datetime.date, departure_id: str, destination_id: str) -> list[ContainerItem]:
    containers = await load_containers()
    return transform_containers(containers)
