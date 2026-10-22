from fastapi_another_jwt_auth import AuthJWT
from shared.config import Settings


def require_token(authorization: AuthJWT, settings: Settings, disabled: bool) -> None:
    """Check the token of the caller, unless the app switched the check off."""
    if not disabled:
        authorization.jwt_required()
