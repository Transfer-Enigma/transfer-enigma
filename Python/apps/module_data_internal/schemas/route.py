import datetime
import enum

from module_shared.database import Base
from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import CompanyModel, ContainerModel, ServiceModel
from .point import PointModel


class RouteType(enum.Enum):
    SEA = "SEA"
    RAIL = "RAIL"


class ContainerTransferTerms(enum.Enum):
    FIFO = "FIFO"
    FILO = "FILO"
    LIFO = "LIFO"
    LILO = "LILO"


class ContainerShipmentTerms(enum.Enum):
    FOR = "FOR"
    FOB = "FOB"
    FCA = "FCA"


class ContainerOwner(enum.Enum):
    COC = "COC"  # The line provides an equipment
    SOC = "SOC"  # The expeditor provides an equipment


class PriceModel(Base):
    uid = (
        "route_id",
        "container_id",
    )

    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint(*uid, name="uk__fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)  # noqa: A003

    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", name="fk__price_route", ondelete="CASCADE"))
    container_id: Mapped[int] = mapped_column(ForeignKey("containers.id", name="fk__price_container"))

    value: Mapped[float | None] = mapped_column(nullable=True, default=None)
    currency: Mapped[str] = mapped_column(String(10))
    conversation_percents: Mapped[float] = mapped_column(default=0)

    container: Mapped[ContainerModel] = relationship()
    route: Mapped['RouteSegmentModel'] = relationship("RouteSegmentModel", back_populates="prices")


class RouteSegmentModel(Base):
    uid = (
        "company_id",
        "start_point_id",
        "end_point_id",
        "dropp_off_point_id",
        "effective_from",
        "effective_to",
        "container_shipment_terms",
        "container_transfer_terms",
        "container_owner",
        "is_through",
    )

    __tablename__ = "routes"
    __table_args__ = (UniqueConstraint(*uid, name="uk__fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)  # noqa: A003

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", name="fk__route_company"))
    start_point_id: Mapped[int] = mapped_column(ForeignKey("points.id", name="fk__route_point__start"))
    end_point_id: Mapped[int] = mapped_column(ForeignKey("points.id", name="fk__route_point__end"))

    dropp_off_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("points.id", name="fk__route_point__dropp_off"),
        nullable=True,
    )

    effective_from: Mapped[datetime.date] = mapped_column(DateTime(timezone=False))
    effective_to: Mapped[datetime.date] = mapped_column(DateTime(timezone=False))
    comment: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    timetable: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)

    is_through: Mapped[bool] = mapped_column(default=True)

    type: Mapped[RouteType] = mapped_column(  # noqa: A003
        Enum(
            RouteType,
            create_constraint=True,
            check_constraint=True,
            validate_strings=True,
        )
    )
    container_transfer_terms: Mapped[ContainerTransferTerms] = mapped_column(
        Enum(
            ContainerTransferTerms,
            create_constraint=True,
            check_constraint=True,
            validate_strings=True,
        )
    )
    container_shipment_terms: Mapped[ContainerShipmentTerms] = mapped_column(
        Enum(
            ContainerShipmentTerms,
            create_constraint=True,
            check_constraint=True,
            validate_strings=True,
        )
    )
    container_owner: Mapped[ContainerOwner] = mapped_column(
        Enum(
            ContainerOwner,
            create_constraint=True,
            check_constraint=True,
            validate_strings=True,
        )
    )

    start_point: Mapped[PointModel] = relationship(PointModel, foreign_keys=[start_point_id])
    end_point: Mapped[PointModel] = relationship(PointModel, foreign_keys=[end_point_id])
    dropp_off_point: Mapped[PointModel] = relationship(PointModel, foreign_keys=[dropp_off_point_id])
    company: Mapped[CompanyModel] = relationship()
    prices: Mapped[list[PriceModel]] = relationship("PriceModel", back_populates="route")
    services: Mapped[list['ServicePriceModel']] = relationship("ServicePriceModel", back_populates="route")


class ServicePriceModel(Base):
    uid = ("route_id", "service_id", "container_id")

    __tablename__ = "service_prices"

    id: Mapped[int] = mapped_column(primary_key=True)  # noqa: A003

    route_id: Mapped[int] = mapped_column(
        ForeignKey(f"{RouteSegmentModel.__tablename__}.id", name="fk__service_prices_route"),
        nullable=False,
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey(f"{ServiceModel.__tablename__}.id", name="fk__service_prices_service"),
        nullable=False,
    )
    container_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{ContainerModel.__tablename__}.id", name="fk__service_prices_container"),
        nullable=True,
        default=None,
    )

    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[float] = mapped_column(nullable=False)

    route: Mapped[RouteSegmentModel] = relationship(back_populates="services")
    service: Mapped[ServiceModel] = relationship()
    container: Mapped[ContainerModel | None] = relationship()
