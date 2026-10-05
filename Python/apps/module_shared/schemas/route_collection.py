import datetime

from module_shared.database import Base
from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


class RouteCollectionModel(Base):
    """A permanent подборка of route links.

    If demo_uid is set, the collection was created from a demo link and is
    available via the owning demo link as well as via the main link with
    authorization. Collections without demo_uid are never available via demo.
    """

    __tablename__ = "route_collections"

    uid: Mapped[str] = mapped_column(String(32), primary_key=True)

    demo_uid: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None, index=True)

    items: Mapped[list] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False), default=datetime.datetime.now)
