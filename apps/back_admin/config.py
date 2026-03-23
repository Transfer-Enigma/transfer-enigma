from functools import cache

from pydantic_settings import BaseSettings


@cache
def get_settings():
    return Settings()


class Settings(BaseSettings):
    GSHEETS_URL: str
    ROUTES_WS: str
    POINTS_WS: str

    GOOGLE_SERVICE_ACCOUNT_FILE_PATH: str = "back_admin/resources/google_service_account.json"
    DEFAULT_UPLOADER_FIELDS_CONFIG_PATH: str = "back_admin/resources/uploader_fields_config.json"
