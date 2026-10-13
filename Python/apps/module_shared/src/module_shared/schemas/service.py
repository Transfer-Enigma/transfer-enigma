from module_shared.database import Base
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column


class ServiceModel(Base):
    uid = ("name",)

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)  # noqa: A003
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    internal_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    hint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    mandatory: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    default: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
