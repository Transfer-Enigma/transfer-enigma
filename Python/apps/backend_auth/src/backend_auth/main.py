from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED

import bcrypt
from fastapi_another_jwt_auth import AuthJWT
from fastapi_another_jwt_auth.exceptions import AuthJWTException
from module_shared.config import Settings, get_settings
from module_shared.jwt_error_handler import authjwt_exception_handler
from module_shared.logger import setup_logging, setup_sqlalchemy_logging
from pydantic import BaseModel

shared_settings = get_settings()

AuthJWT.load_config(get_settings)
app = FastAPI(redirect_slashes=False)

setup_logging("backend_auth", shared_settings.LOG_LEVEL)
setup_sqlalchemy_logging(shared_settings.DB_LOG_LEVEL, shared_settings.DB_LOG_OUTPUT)


class User(BaseModel):
    login: str
    password: str


app.add_exception_handler(AuthJWTException, authjwt_exception_handler)


@app.post("/login")
def login(user: User, Authorize: Annotated[AuthJWT, Depends()], settings: Annotated[Settings, Depends(get_settings)]):
    """
    Login using username and password.
    Setting up JWT cookie if login was successful.
    """

    admin_pass_bytes = settings.admin_password.encode("utf-8")
    pass_salt = bcrypt.gensalt()
    admin_password_hash = bcrypt.hashpw(admin_pass_bytes, pass_salt)

    user_pass_bytes = user.password.encode("utf-8")
    user_password_hash = bcrypt.hashpw(user_pass_bytes, pass_salt)

    if user.login != settings.admin_login or user_password_hash != admin_password_hash:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Incorrect login or password")

    access_token = Authorize.create_access_token(subject=user.login)
    refresh_token = Authorize.create_refresh_token(subject=user.login)

    # Set the JWT and CSRF double submit cookies in the response
    Authorize.set_access_cookies(access_token)
    Authorize.set_refresh_cookies(refresh_token)

    headers = {}
    if settings.access_token_expire_minutes:
        headers["X-Access-Token-Expires"] = str(settings.access_token_expire_minutes)
    if settings.refresh_token_expire_minutes:
        headers["X-Refresh-Token-Expires"] = str(settings.refresh_token_expire_minutes)

    return JSONResponse(headers=Authorize._response.headers | headers, content={"status": "OK"})


@app.post("/token/refresh")
def refresh(Authorize: Annotated[AuthJWT, Depends()], settings: Annotated[Settings, Depends(get_settings)]):
    """Token refreshing."""

    Authorize.jwt_refresh_token_required()
    current_user = Authorize.get_jwt_subject()
    new_access_token = Authorize.create_access_token(subject=current_user)

    # Set the JWT and CSRF double submit cookies in the response
    Authorize.set_access_cookies(new_access_token)

    headers = {}
    if settings.access_token_expire_minutes:
        headers["X-Access-Token-Expires"] = str(settings.access_token_expire_minutes)
    if settings.refresh_token_expire_minutes:
        headers["X-Refresh-Token-Expires"] = str(settings.refresh_token_expire_minutes)

    return JSONResponse(headers=headers, content={"status": "OK"})


@app.delete("/logout")
def logout(Authorize: Annotated[AuthJWT, Depends()]):
    """
    Because the JWT are stored in an httponly cookie now, we cannot
    log the user out by simply deleting the cookie in the frontend.
    We need the backend to send us a response to delete the cookies.
    """

    Authorize.jwt_required()
    Authorize.unset_jwt_cookies()

    return {"status": "OK"}


@app.get("/me")
def hello(Authorize: Annotated[AuthJWT, Depends()]):
    """Get user info."""

    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()

    return {"username": current_user}
