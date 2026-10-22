import datetime

from data.repositories.containers import get_containers as load_containers
from shared.dto.route import ContainerItem

from .transformers.containers import transform_containers


async def get_containers(date: datetime.date, departure_id: str, destination_id: str) -> list[ContainerItem]:
    containers = await load_containers()
    return transform_containers(containers)


def search_container_ids(containers: list, weight: int, size: int):
    return [
        c.id
        for c in containers
        if c.size == size
        and c.weight_from <= weight <= c.weight_to
    ]
