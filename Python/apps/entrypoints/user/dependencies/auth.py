from typing import Annotated

from fastapi import Depends

from fastapi_another_jwt_auth import AuthJWT
from shared.config import Settings, get_settings


def request_auth(authorization: Annotated[AuthJWT, Depends()], settings: Annotated[Settings, Depends(get_settings)]):
<<<<<<< HEAD
    if not settings.DISABLE_ADMIN_AUTH_CHECK:
=======
    if not settings.DISABLE_USER_AUTH_CHECK:
>>>>>>> 27ce1f08 (Python: Rename packages by architecture layer)
        authorization.jwt_required()
