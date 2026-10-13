from functools import cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DISABLE_USER_AUTH_CHECK: bool = False


@cache
def get_settings():
    return Settings()
