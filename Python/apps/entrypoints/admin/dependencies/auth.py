from typing import Annotated

from fastapi import Depends

from fastapi_another_jwt_auth import AuthJWT
from shared.auth import require_token
from shared.config import Settings, get_settings


def request_auth(authorization: Annotated[AuthJWT, Depends()], settings: Annotated[Settings, Depends(get_settings)]):
    require_token(authorization, settings, settings.DISABLE_ADMIN_AUTH_CHECK)
