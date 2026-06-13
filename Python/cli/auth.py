import json
import logging
from pathlib import Path

import aiohttp

from .config import get_cli_settings

logger = logging.getLogger(__name__)


def _token_path() -> Path:
    return Path(get_cli_settings().TOKEN_FILE).expanduser()


def get_stored_token() -> str | None:
    path = _token_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data.get("access_token")
    except (json.JSONDecodeError, KeyError):
        return None


def store_token(access_token: str) -> None:
    path = _token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"access_token": access_token}))


def clear_token() -> None:
    path = _token_path()
    if path.exists():
        path.unlink()


def make_cookie_header(token: str) -> dict[str, str]:
    return {"Cookie": f"access_token_cookie={token}"}


async def login(api_url: str, username: str, password: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{api_url}/login",
            json={"login": username, "password": password},
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"Login failed (HTTP {resp.status}): {body}")

            token = None
            for cookie in resp.cookies.values():
                if cookie.key == "access_token_cookie":
                    token = cookie.value
                    break

            if not token:
                raise RuntimeError("No access_token_cookie in login response")

            return token


def ensure_token() -> str:
    token = get_stored_token()
    if not token:
        raise RuntimeError(
            "Not authenticated. Run 'python -m cli login' first."
        )
    return token
