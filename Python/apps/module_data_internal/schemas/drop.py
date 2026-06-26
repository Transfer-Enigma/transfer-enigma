import datetime

from module_shared.database import Base
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import CompanyModel, ContainerModel
from .point import PointModel


class DropOffModel(Base):
    uid = (
        "start_point_id",
        "end_point_id",
        "container_id",
        "company_id",
        "effective_from",
        "effective_to",
    )

    __tablename__ = "drop"
    __table_args__ = (UniqueConstraint(*uid, name="uk__fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)  # noqa: A003

    container_id: Mapped[int] = mapped_column(ForeignKey("containers.id", name="fk__drop_container"))
    # SEA COMPANY
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", name="fk__drop_companies"))
    # RAIL POINTS
    start_point_id: Mapped[int | None] = mapped_column(ForeignKey("points.id", name="fk__drop_point__start"))
    end_point_id: Mapped[int | None] = mapped_column(ForeignKey("points.id", name="fk__drop_point__end"))

    effective_from: Mapped[datetime.date] = mapped_column(DateTime(timezone=False))
    effective_to: Mapped[datetime.date] = mapped_column(DateTime(timezone=False))
    price: Mapped[float] = mapped_column(default=0)
    conversation_percents: Mapped[float] = mapped_column(default=0)
    currency: Mapped[str] = mapped_column(String(25))

    start_point: Mapped[PointModel | None] = relationship(
        PointModel, foreign_keys=[start_point_id]
    )
    end_point: Mapped[PointModel | None] = relationship(
        PointModel, foreign_keys=[end_point_id]
    )
    company: Mapped[CompanyModel] = relationship()
    container: Mapped[ContainerModel] = relationship()
