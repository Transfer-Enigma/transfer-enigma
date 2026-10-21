import datetime

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 26db16b4 (Python: Rename shared models and schemas packages)
from shared.orm.company import CompanyModel
from shared.orm.container import ContainerModel, ContainerType
from shared.orm.drop import DropModel
from shared.orm.point import PointModel
from shared.orm.route import (
<<<<<<< HEAD
=======
from shared.schemas.company import CompanyModel
from shared.schemas.container import ContainerModel, ContainerType
from shared.schemas.drop import DropModel
from shared.schemas.point import PointModel
from shared.schemas.route import (
>>>>>>> a90e866f (Python: Rename packages by architecture layer)
=======
>>>>>>> 26db16b4 (Python: Rename shared models and schemas packages)
    ContainerOwner,
    ContainerShipmentTerms,
    ContainerTransferTerms,
    PriceModel,
    RouteModel,
    RouteType,
    ServicePriceModel,
)
<<<<<<< HEAD
<<<<<<< HEAD
from shared.orm.service import ServiceModel
=======
from shared.schemas.service import ServiceModel
>>>>>>> a90e866f (Python: Rename packages by architecture layer)
=======
from shared.orm.service import ServiceModel
>>>>>>> 26db16b4 (Python: Rename shared models and schemas packages)

__all__ = (
    "CompanyFactory",
    "PointFactory",
    "ContainerFactory",
    "RouteFactory",
    "PriceFactory",
    "ServiceFactory",
    "ServicePriceFactory",
    "DropFactory",
)


def CompanyFactory(**kwargs) -> CompanyModel:
    defaults = {"name": "TestCompany"}
    return CompanyModel(**{**defaults, **kwargs})


def PointFactory(**kwargs) -> PointModel:
    defaults = {
        "city": "TestCity",
        "country": "TC",
        "RU_city": "ТестСити",
        "RU_country": "ТестСтрана",
    }
    return PointModel(**{**defaults, **kwargs})


def ContainerFactory(**kwargs) -> ContainerModel:
    defaults = {
        "size": 20,
        "weight_from": 0,
        "weight_to": 28000,
        "name": "20DC",
        "type": ContainerType.DC,
    }
    return ContainerModel(**{**defaults, **kwargs})


def RouteFactory(**kwargs) -> RouteModel:
    defaults = {
        "effective_from": datetime.date(2024, 1, 1),
        "effective_to": datetime.date(2025, 12, 31),
        "type": RouteType.RAIL,
        "container_transfer_terms": ContainerTransferTerms.FIFO,
        "container_shipment_terms": ContainerShipmentTerms.FOB,
        "container_owner": ContainerOwner.COC,
        "is_through": False,
        "comment": None,
        "timetable": None,
    }
    return RouteModel(**{**defaults, **kwargs})


def PriceFactory(**kwargs) -> PriceModel:
    defaults = {
        "value": 1000.0,
        "currency": "USD",
        "conversation_percents": 0,
    }
    return PriceModel(**{**defaults, **kwargs})


def ServiceFactory(**kwargs) -> ServiceModel:
    defaults = {
        "name": "Test Service",
        "internal_name": "test_service",
        "description": "A test service",
        "hint": None,
        "mandatory": False,
        "default": True,
    }
    return ServiceModel(**{**defaults, **kwargs})


def ServicePriceFactory(**kwargs) -> ServicePriceModel:
    defaults = {
        "currency": "USD",
        "price": 100.0,
    }
    return ServicePriceModel(**{**defaults, **kwargs})


def DropFactory(**kwargs) -> DropModel:
    defaults = {
        "effective_from": datetime.date(2024, 1, 1),
        "effective_to": datetime.date(2025, 12, 31),
        "price": 500.0,
        "conversation_percents": 0,
        "currency": "USD",
    }
    return DropModel(**{**defaults, **kwargs})
