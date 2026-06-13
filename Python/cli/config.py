from functools import cache
from pathlib import Path

from pydantic_settings import BaseSettings


@cache
def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _env_file():
    root = _project_root()
    return root / ".env.cli"


@cache
def get_cli_settings():
    return CLISettings()


class CLISettings(BaseSettings):
    ADMIN_USER: str
    ADMIN_PASSWORD: str

    API_BASE_URL: str = "http://localhost/api"
    ADMIN_API_BASE_URL: str = "http://localhost/admin/api"
    AUTH_API_URL: str = "http://localhost/api/user"
    TOKEN_FILE: str = "~/.opencode-token"

    GSHEETS_URL: str = ""
    GOOGLE_SERVICE_ACCOUNT_PATH: str = ""

    model_config = {
        "env_file": _env_file(),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
