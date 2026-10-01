import datetime
import hashlib
import json

from module_shared.schemas.drop import DropModel
from module_shared.schemas.route import RouteModel


def _norm_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text.lower()


def _norm_date(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    return str(value)


def _norm_enum(value):
    if value is None:
        return None
    normalized = getattr(value, "value", value)
    if isinstance(normalized, str):
        return normalized.strip().upper()
    return normalized


def _norm_number(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    return value


def _container_key(container) -> list:
    return [
        container.size,
        _norm_enum(container.type),
        container.weight_from,
        container.weight_to,
    ]


def _hash_payload(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def identity_uid(scope: str, fields: dict) -> str:
    return _hash_payload({"scope": scope, **fields})


def natural_uid_for_route_values(values: dict) -> str:
    return identity_uid("route", {
        "type": _norm_enum(values.get("type")),
        "company": _norm_text(values.get("company")),
        "start_point": _norm_text(values.get("start_point")),
        "end_point": _norm_text(values.get("end_point")),
        "dropp_off_point": _norm_text(values.get("dropp_off_point")),
        "effective_from": _norm_date(values.get("effective_from")),
        "effective_to": _norm_date(values.get("effective_to")),
        "container_shipment_terms": _norm_enum(values.get("container_shipment_terms")),
        "container_transfer_terms": _norm_enum(values.get("container_transfer_terms")),
        "container_owner": _norm_enum(values.get("container_owner")),
        "is_through": bool(values.get("is_through", True)),
    })


def natural_uid_for_dropp_values(values: dict) -> str:
    return identity_uid("dropp", {
        "start_point": _norm_text(values.get("start_point")),
        "end_point": _norm_text(values.get("end_point")),
        "company": _norm_text(values.get("company")),
        "effective_from": _norm_date(values.get("effective_from")),
        "effective_to": _norm_date(values.get("effective_to")),
    })


def payload_uid_for_route_values(values: dict, prices: dict) -> str:
    return identity_uid("route-payload", {
        "natural": natural_uid_for_route_values(values),
        "prices": {key: _norm_number(value) for key, value in sorted(prices.items())},
    })


def payload_uid_for_dropp_values(values: dict, prices: dict) -> str:
    return identity_uid("dropp-payload", {
        "natural": natural_uid_for_dropp_values(values),
        "prices": {key: _norm_number(value) for key, value in sorted(prices.items())},
    })


def natural_uid_for_route_model(route: RouteModel) -> str:
    return natural_uid_for_route_values({
        "type": route.type,
        "company": route.company.name,
        "start_point": route.start_point.city,
        "end_point": route.end_point.city,
        "dropp_off_point": route.dropp_off_point.city if route.dropp_off_point else None,
        "effective_from": route.effective_from,
        "effective_to": route.effective_to,
        "container_shipment_terms": route.container_shipment_terms,
        "container_transfer_terms": route.container_transfer_terms,
        "container_owner": route.container_owner,
        "is_through": route.is_through,
    })


def natural_uid_for_dropp_item(item: DropModel) -> str:
    return natural_uid_for_dropp_values({
        "start_point": item.start_point.city if item.start_point else None,
        "end_point": item.end_point.city if item.end_point else None,
        "company": item.company.name,
        "effective_from": item.effective_from,
        "effective_to": item.effective_to,
    })


def fingerprint_route(route: RouteModel) -> str:
    payload = {
        "type": _norm_enum(route.type),
        "company": _norm_text(route.company.name),
        "start_point": _norm_text(route.start_point.city),
        "end_point": _norm_text(route.end_point.city),
        "dropp_off_point": _norm_text(route.dropp_off_point.city) if route.dropp_off_point else None,
        "effective_from": _norm_date(route.effective_from),
        "effective_to": _norm_date(route.effective_to),
        "container_shipment_terms": _norm_enum(route.container_shipment_terms),
        "container_transfer_terms": _norm_enum(route.container_transfer_terms),
        "container_owner": _norm_enum(route.container_owner),
        "is_through": bool(route.is_through),
        "prices": sorted(
            [
                [*_container_key(price.container), price.value,
                 _norm_text(price.currency)]
                for price in route.prices
            ],
            key=str,
        ),
        "services": sorted(
            [
                [
                    service.service.internal_name,
                    _container_key(service.container) if service.container else None,
                    service.price,
                    _norm_text(service.currency),
                ]
                for service in route.services
            ],
            key=str,
        ),
    }
    return _hash_payload(payload)


def fingerprint_drop(item: DropModel) -> str:
    payload = {
        "start_point": _norm_text(item.start_point.city),
        "end_point": _norm_text(item.end_point.city),
        "company": _norm_text(item.company.name),
        "container": _container_key(item.container),
        "effective_from": _norm_date(item.effective_from),
        "effective_to": _norm_date(item.effective_to),
        "price": item.price,
        "currency": _norm_text(item.currency),
    }
    return _hash_payload(payload)
