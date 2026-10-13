from module_shared.database import Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class CompanyModel(Base):
    uid = ("name",)

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)  # noqa: A003
    name: Mapped[str] = mapped_column(String(150), unique=True)
