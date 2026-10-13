from decimal import Decimal

from module_shared.database import Base
from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column


class DemoGuestModel(Base):
    __tablename__ = "demo_guests"

    id: Mapped[int] = mapped_column(primary_key=True)  # noqa: A003
    uid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sea_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    sea_profit_currency: Mapped[str] = mapped_column(String(3), default="USD")
    rail_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    rail_profit_currency: Mapped[str] = mapped_column(String(3), default="USD")
