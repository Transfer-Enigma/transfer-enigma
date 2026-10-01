import datetime
import hashlib
import json


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
