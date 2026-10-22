from contextlib import asynccontextmanager
from importlib.util import find_spec

from fastapi import FastAPI

from data.cache.registry import get_cache_registry
from fastapi_another_jwt_auth import AuthJWT
from fastapi_another_jwt_auth.exceptions import AuthJWTException
from shared.config import get_settings
from shared.database import get_database
from shared.domain_error_handler import (
    not_found_error_handler,
    resource_permission_error_handler,
    validation_error_handler,
)
from shared.dto.errors import NotFoundError, ResourcePermissionError, ValidationError
from shared.jwt_error_handler import authjwt_exception_handler
from shared.logger import setup_logging, setup_sqlalchemy_logging
from shared.redis_client import get_redis_client

from .autodiscover import api_discover

if find_spec("dotenv") is not None:
    from dotenv import load_dotenv

    load_dotenv()

shared_settings = get_settings()

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
    await get_cache_registry().load()
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

if not shared_settings.DISABLE_ADMIN_AUTH_CHECK:
    # Configure AuthJWT with settings
    AuthJWT.load_config(get_settings)

    # Exception handler for JWT errors
    app.add_exception_handler(AuthJWTException, authjwt_exception_handler)

# Exception handlers for domain errors raised in the data layer
app.add_exception_handler(NotFoundError, not_found_error_handler)
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(ResourcePermissionError, resource_permission_error_handler)


routers = api_discover()
for router in routers:
    app.include_router(router)
