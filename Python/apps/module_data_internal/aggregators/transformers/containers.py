from module_shared.models.route import ContainerItem
from module_shared.schemas.container import ContainerModel


def transform_container(container: ContainerModel) -> ContainerItem:
    return ContainerItem(
        id=container.id,
        type=container.type.value,
        size=container.size,
        weight_from=container.weight_from,
        weight_to=container.weight_to,
        name=container.name,
    )


def transform_containers(containers: list[ContainerModel]) -> list[ContainerItem]:
    return [transform_container(c) for c in containers]
