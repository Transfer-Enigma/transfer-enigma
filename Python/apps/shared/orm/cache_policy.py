from shared.database import Base
from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class CachePolicyModel(Base):
    uid = ("source", "entity")

    __tablename__ = "cache_policies"
    __table_args__ = (UniqueConstraint(*uid, name="uk__cache_policy_source_entity"),)

    id: Mapped[int] = mapped_column(primary_key=True)  # noqa: A003
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    entity: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ttl: Mapped[int] = mapped_column(Integer, nullable=False)
