from datetime import date, datetime
from decimal import Decimal

from module_shared.database import Base
from sqlalchemy import Date, DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class RateModel(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("code", "date", name="uq_exchange_rates_code_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)  # noqa: A003
    code: Mapped[str] = mapped_column(String(3), index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    date: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
