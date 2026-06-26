import datetime

from module_data_internal.schemas import (
    CompanyModel,
    ContainerModel,
    ContainerOwner,
    ContainerShipmentTerms,
    ContainerTransferTerms,
    ContainerType,
    DropOffModel,
    PointModel,
    PriceModel,
    RouteSegmentModel,
    RouteType,
    ServiceModel,
    ServicePriceModel,
)

__all__ = (
    "CompanyFactory",
    "PointFactory",
    "ContainerFactory",
    "RouteSegmentFactory",
    "PriceFactory",
    "ServiceFactory",
    "ServicePriceFactory",
    "DropOffFactory",
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


def RouteSegmentFactory(**kwargs) -> RouteSegmentModel:
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
    return RouteSegmentModel(**{**defaults, **kwargs})


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


def DropOffFactory(**kwargs) -> DropOffModel:
    defaults = {
        "effective_from": datetime.date(2024, 1, 1),
        "effective_to": datetime.date(2025, 12, 31),
        "price": 500.0,
        "conversation_percents": 0,
        "currency": "USD",
    }
    return DropOffModel(**{**defaults, **kwargs})
