from functools import cache

from pydantic_settings import BaseSettings


@cache
def get_settings():
    return Settings()


class Settings(BaseSettings):
    DISABLE_ADMIN_AUTH_CHECK: bool = False

    DEFAULT_GSHEETS_URL: str
    DEFAULT_SEA_ROUTES_WS: str
    DEFAULT_RAIL_ROUTES_WS: str
    DEFAULT_TRUCK_ROUTES_WS: str
    DEFAULT_DROPP_ROUTES_WS: str
    DEFAULT_POINTS_WS: str
    DEFAULT_SERVICES_WS: str

    GOOGLE_SERVICE_ACCOUNT_RESOURCE_NAME: str = "google_service_account.json"
    DEFAULT_UPLOADER_FIELDS_CONFIG_RESOURCE_NAME: str = "uploader_fields_config.json"
