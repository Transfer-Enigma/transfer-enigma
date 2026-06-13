import asyncio
import logging

import click

from .auth import clear_token, login, store_token
from .config import get_cli_settings
from .db_explorer import db
from .route_query import route_query
from .sheets_reader import sheets

logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@cli.command("login")
@click.option(
    "--username",
    default=get_cli_settings().ADMIN_USER,
    prompt=True,
    help="Admin username",
)
@click.option(
    "--password",
    default=get_cli_settings().ADMIN_PASSWORD,
    prompt=True,
    hide_input=True,
    help="Admin password",
)
@click.option("--api-url", default=None, help="Auth API URL")
def login_command(username: str, password: str, api_url: str | None):
    """Authenticate and store JWT token."""
    settings = get_cli_settings()
    url = api_url or settings.AUTH_API_URL

    try:
        token = asyncio.run(login(url, username, password))
        store_token(token)
        click.echo("Login successful")
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort from e


@cli.command("logout")
def logout_command():
    """Clear stored JWT token."""
    clear_token()
    click.echo("Logged out")


cli.add_command(route_query, "route-query")
cli.add_command(sheets, "sheets")
cli.add_command(db, "db")
