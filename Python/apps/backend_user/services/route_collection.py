import logging
import uuid

from backend_user.schemas.route_collections import CollectionItem
from backend_user.services.route_link import get_route_by_link
from module_shared.database import get_database
from module_shared.models.route import RouteResult
from module_shared.schemas.route_collection import RouteCollectionModel
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def create_collection(items: list[CollectionItem], demo_uid: str | None) -> RouteCollectionModel:
    """Validate route links and store them as a permanent collection.

    Raises RouteLinkNotFoundError if any item does not form a valid route.
    """
    stored: list[dict] = []
    for item in items:
        await get_route_by_link(item.segments, item.services)
        stored.append({"segments": item.segments, "services": item.services})

    model = RouteCollectionModel(uid=uuid.uuid4().hex, demo_uid=demo_uid, items=stored)
    async with get_database().session_context() as session:
        session.add(model)

    logger.info("Route collection created: uid=%s demo=%s items=%d", model.uid, demo_uid, len(stored))
    return model


async def get_collection(uid: str) -> RouteCollectionModel | None:
    async with get_database().session_context() as session:
        result = await session.execute(
            select(RouteCollectionModel).where(RouteCollectionModel.uid == uid)
        )
        return result.scalars().first()


async def resolve_collection(collection: RouteCollectionModel) -> list[RouteResult]:
    """Build RouteResults for every stored item.

    Raises RouteLinkNotFoundError if any stored item is no longer valid.
    """
    routes: list[RouteResult] = []
    for item in collection.items:
        routes.append(await get_route_by_link(item["segments"], item.get("services", [])))
    return routes
