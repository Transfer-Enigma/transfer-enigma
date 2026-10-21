<<<<<<< HEAD
from collections.abc import AsyncIterator
=======
>>>>>>> 27ce1f08 (Python: Rename packages by architecture layer)
from typing import Annotated

from fastapi import Depends, Request

<<<<<<< HEAD
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
=======
from fastapi_another_jwt_auth import AuthJWT
from pydantic import BaseModel
from shared.config import Settings, get_settings
from shared.database import Database, get_database
from shared.repositories.demo_guest import get_demo_guest_by_uid

from .auth import request_auth


class AuthContext(BaseModel):
    is_demo: bool = False
    sea_profit: float = 0.0
    sea_profit_currency: str = "USD"
    rail_profit: float = 0.0
    rail_profit_currency: str = "USD"
    demo_uid: str | None = None


async def get_auth_context(
>>>>>>> 27ce1f08 (Python: Rename packages by architecture layer)
    request: Request,
    authorization: Annotated[AuthJWT, Depends()],
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
<<<<<<< HEAD
) -> CallerContext:
    """Resolve who is calling.

    A demo guest is recognized by the header, everybody else must carry a
    valid token. An unknown demo uid falls back to the regular caller.
    """
    demo_uid = request.headers.get("X-Demo-User-UID")
    if not demo_uid:
        request_auth(authorization, settings)
        return CallerContext(kind=ContextKind.ADMIN)
=======
) -> AuthContext:
    demo_uid = request.headers.get("X-Demo-User-UID")
    if not demo_uid:
        request_auth(authorization, settings)
        return AuthContext()
>>>>>>> 27ce1f08 (Python: Rename packages by architecture layer)

    async with db.session_context() as session:
        guest = await get_demo_guest_by_uid(session, demo_uid)

    if not guest:
<<<<<<< HEAD
        return CallerContext(kind=ContextKind.ADMIN)

    return CallerContext(
        kind=ContextKind.DEMO,
        identity=demo_uid,
=======
        return AuthContext()

    return AuthContext(
        is_demo=True,
        demo_uid=demo_uid,
>>>>>>> 27ce1f08 (Python: Rename packages by architecture layer)
        sea_profit=float(guest.sea_profit),
        sea_profit_currency=guest.sea_profit_currency,
        rail_profit=float(guest.rail_profit),
        rail_profit_currency=guest.rail_profit_currency,
<<<<<<< HEAD
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
=======
    )
>>>>>>> 27ce1f08 (Python: Rename packages by architecture layer)
