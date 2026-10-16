import datetime

from module_shared.database import Base
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class SyncDocumentModel(Base):
    __tablename__ = "sync_documents"

    id: Mapped[int] = mapped_column(primary_key=True)  # noqa: A003
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(20), default="gsheets")
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    sea_ws: Mapped[str | None] = mapped_column(String(200), nullable=True, default=None)
    rail_ws: Mapped[str | None] = mapped_column(String(200), nullable=True, default=None)
    truck_ws: Mapped[str | None] = mapped_column(String(200), nullable=True, default=None)
    dropp_ws: Mapped[str | None] = mapped_column(String(200), nullable=True, default=None)
    points_ws: Mapped[str | None] = mapped_column(String(200), nullable=True, default=None)
    services_ws: Mapped[str | None] = mapped_column(String(200), nullable=True, default=None)
    uid_column: Mapped[str] = mapped_column(String(100), default="__uid")
    last_status: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    last_errors_count: Mapped[int] = mapped_column(Integer(), default=0)
    loaded_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=False), nullable=True,
                                                                default=None)
