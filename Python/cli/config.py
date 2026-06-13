from functools import cache

from pydantic_settings import BaseSettings


@cache
def get_cli_settings():
    return CLISettings()


class CLISettings(BaseSettings):
    API_BASE_URL: str = "http://localhost/api"
    ADMIN_API_BASE_URL: str = "http://localhost/admin/api"
    AUTH_API_URL: str = "http://localhost/api/user"
    TOKEN_FILE: str = "~/.opencode-token"

    GSHEETS_URL: str = ""
    GOOGLE_SERVICE_ACCOUNT_PATH: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
