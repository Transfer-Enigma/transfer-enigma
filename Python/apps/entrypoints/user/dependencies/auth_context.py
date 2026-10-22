from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request

from data.cache.settings import get_setting_cached
from data.repositories.demo_guests import get_demo_guest_by_uid
from fastapi_another_jwt_auth import AuthJWT
from shared.config import Settings, get_settings
from shared.context import CallerContext, ContextKind, reset_context, set_context
from shared.database import Database, get_database

from .auth import request_auth

DEMO_EXCLUDED_FIELDS_SETTING = ("feature-flag", "demo-excluded-fields")


async def _demo_excluded_fields() -> list[str]:
    """The fields a demo guest must not see."""
    setting = await get_setting_cached(*DEMO_EXCLUDED_FIELDS_SETTING)
    if setting is None or not isinstance(setting.value, list):
        return []
    return list(setting.value)


async def get_caller_context(
    request: Request,
    authorization: Annotated[AuthJWT, Depends()],
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CallerContext:
    """Resolve who is calling.

    A demo guest is recognized by the header, everybody else must carry a
    valid token. An unknown demo uid falls back to the regular caller.
    """
    demo_uid = request.headers.get("X-Demo-User-UID")
    if not demo_uid:
        request_auth(authorization, settings)
        return CallerContext(kind=ContextKind.ADMIN)

    async with db.session_context() as session:
        guest = await get_demo_guest_by_uid(session, demo_uid)

    if not guest:
        return CallerContext(kind=ContextKind.ADMIN)

    return CallerContext(
        kind=ContextKind.DEMO,
        identity=demo_uid,
        sea_profit=float(guest.sea_profit),
        sea_profit_currency=guest.sea_profit_currency,
        rail_profit=float(guest.rail_profit),
        rail_profit_currency=guest.rail_profit_currency,
        excluded_fields=await _demo_excluded_fields(),
    )


async def bind_caller_context(
    context: Annotated[CallerContext, Depends(get_caller_context)],
) -> AsyncIterator[CallerContext]:
    """Bind the context of the request, so that the services can read it."""
    token = set_context(context)
    try:
        yield context
    finally:
        reset_context(token)
