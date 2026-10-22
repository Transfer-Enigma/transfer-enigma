from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from fastapi_another_jwt_auth import AuthJWT
from shared.config import Settings, get_settings
from shared.context import CallerContext, ContextKind, reset_context, set_context

from .auth import request_auth


async def bind_caller_context(
    authorization: Annotated[AuthJWT, Depends()],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[CallerContext]:
    """Bind the context of the request, so that the services can read it."""
    request_auth(authorization, settings)
    context = CallerContext(kind=ContextKind.ADMIN)
    token = set_context(context)
    try:
        yield context
    finally:
        reset_context(token)
