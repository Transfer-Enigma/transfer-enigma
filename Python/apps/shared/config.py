from functools import cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str

    # DATABASE
    DB_SCHEME: str
    DB_HOST: str
    DB_PORT: int = 3306

    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    DB_CHARSET: str = "utf8mb4"
    DB_COLLATE: str = "utf8mb4_unicode_ci"
    DB_LOG_LEVEL: str = "WARNING"
    DB_LOG_OUTPUT: str = "both"

    # AUTH
    admin_login: str
    admin_password: str
    jwt_algorithm: str
    authjwt_secret_key: str
    access_token_expire_minutes: int
    refresh_token_expire_minutes: int
    # Configure application to store and get JWT from cookies.
    authjwt_token_location: set = {"cookies"}
    # HTTPS only?
    authjwt_cookie_secure: bool = False
    # CSRF double submit protection.
    authjwt_cookie_csrf_protect: bool = False
    authjwt_cookie_samesite: str = "lax"
    # Per entrypoint switches to skip the JWT check.
    DISABLE_USER_AUTH_CHECK: bool = False
    DISABLE_ADMIN_AUTH_CHECK: bool = False

    # LOGGING
    LOG_LEVEL: str = "INFO"

    # REDIS
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # CACHE
    CACHE_POLICIES_REFRESH_INTERVAL_SECONDS: int = Field(default=10, ge=0)

    # FESCO API
    FESCO_API_KEY: str

    # GOOGLE SHEETS (admin data import)
    DEFAULT_GSHEETS_URL: str
    DEFAULT_SEA_ROUTES_WS: str
    DEFAULT_RAIL_ROUTES_WS: str
    DEFAULT_TRUCK_ROUTES_WS: str
    DEFAULT_DROPP_ROUTES_WS: str
    DEFAULT_POINTS_WS: str
    DEFAULT_SERVICES_WS: str
    GOOGLE_SERVICE_ACCOUNT_RESOURCE_NAME: str = "google_service_account.json"
    DEFAULT_UPLOADER_FIELDS_CONFIG_RESOURCE_NAME: str = "uploader_fields_config.json"

    # RESOURCES
    RESOURCES_BASE_PATH: Path | None = None


@cache
def get_settings():
    return Settings()
