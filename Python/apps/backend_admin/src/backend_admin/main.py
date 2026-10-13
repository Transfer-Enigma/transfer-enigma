from contextlib import asynccontextmanager
from importlib.util import find_spec

from fastapi import FastAPI

from fastapi_another_jwt_auth import AuthJWT
from fastapi_another_jwt_auth.exceptions import AuthJWTException
from module_shared.config import get_settings as get_shared_settings
from module_shared.database import get_database
from module_shared.jwt_error_handler import authjwt_exception_handler
from module_shared.logger import setup_logging, setup_sqlalchemy_logging
from module_shared.redis_client import get_redis_client

from .autodiscover import api_discover
from .config import get_settings

if find_spec("dotenv") is not None:
    from dotenv import load_dotenv

    load_dotenv()

shared_settings = get_shared_settings()

setup_logging("backend_admin", shared_settings.LOG_LEVEL)
setup_sqlalchemy_logging(shared_settings.DB_LOG_LEVEL, shared_settings.DB_LOG_OUTPUT)

# Disable docs in production
docs_url = "/docs" if shared_settings.ENVIRONMENT != "prod" else None
redoc_url = "/redoc" if shared_settings.ENVIRONMENT != "prod" else None
openapi_url = "/openapi.json" if shared_settings.ENVIRONMENT != "prod" else None


@asynccontextmanager
async def lifespan(_: FastAPI):
    await get_database().init()
    await get_redis_client().init()
    yield
    await get_database().close()
    await get_redis_client().close()


app = FastAPI(
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
    redirect_slashes=False,
    lifespan=lifespan,
)

if not get_settings().DISABLE_ADMIN_AUTH_CHECK:
    # Configure AuthJWT with settings
    AuthJWT.load_config(get_shared_settings)

    # Exception handler for JWT errors
    app.add_exception_handler(AuthJWTException, authjwt_exception_handler)


routers = api_discover()
for router in routers:
    app.include_router(router)
