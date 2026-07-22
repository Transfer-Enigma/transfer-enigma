from module_shared.database import Base
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class PointModel(Base):
    uid = ("city", "country")

    __tablename__ = "points"
    __table_args__ = (UniqueConstraint(*uid, name="uk__location"),)

    id: Mapped[int] = mapped_column(primary_key=True)  # noqa: A003
    city: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(50))
    RU_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    RU_country: Mapped[str | None] = mapped_column(String(50), nullable=True)
