from shared.database import Base
from shared.dto.settings import SettingType
from sqlalchemy import Enum, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class SettingModel(Base):
    uid = ("group", "name")

    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint(*uid, name="uk__setting_group_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)  # noqa: A003
    group: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[SettingType] = mapped_column(
        Enum(
            SettingType,
            create_constraint=True,
            check_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked: Mapped[bool] = mapped_column(default=False)
