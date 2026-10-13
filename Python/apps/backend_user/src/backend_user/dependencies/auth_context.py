from typing import Annotated

from fastapi import Depends, Request

from fastapi_another_jwt_auth import AuthJWT
from module_shared.database import Database, get_database
from module_shared.repositories.demo_guest import get_demo_guest_by_uid
from pydantic import BaseModel

from ..config import Settings, get_settings
from .auth import request_auth


class AuthContext(BaseModel):
    is_demo: bool = False
    sea_profit: float = 0.0
    sea_profit_currency: str = "USD"
    rail_profit: float = 0.0
    rail_profit_currency: str = "USD"
    demo_uid: str | None = None


async def get_auth_context(
    request: Request,
    authorization: Annotated[AuthJWT, Depends()],
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthContext:
    demo_uid = request.headers.get("X-Demo-User-UID")
    if not demo_uid:
        request_auth(authorization, settings)
        return AuthContext()

    async with db.session_context() as session:
        guest = await get_demo_guest_by_uid(session, demo_uid)

    if not guest:
        return AuthContext()

    return AuthContext(
        is_demo=True,
        demo_uid=demo_uid,
        sea_profit=float(guest.sea_profit),
        sea_profit_currency=guest.sea_profit_currency,
        rail_profit=float(guest.rail_profit),
        rail_profit_currency=guest.rail_profit_currency,
    )
