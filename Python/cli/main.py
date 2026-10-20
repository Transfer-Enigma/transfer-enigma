import asyncio
import logging

import click

from .auth import clear_token, login, store_token
from .config import get_cli_settings
from .db_explorer import db
from .route_query import route_query
from .sheets_reader import sheets

logger = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context):
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command("login")
@click.option(
    "--username",
    default=None,
    help="Admin username (defaults to ADMIN_USER from .env.cli)",
)
@click.option(
    "--password",
    default=None,
    hide_input=True,
    help="Admin password (defaults to ADMIN_PASSWORD from .env.cli)",
)
@click.option("--api-url", default=None, help="Auth API URL")
def login_command(username: str | None, password: str | None, api_url: str | None):
    """Authenticate and store JWT token."""
    settings = get_cli_settings()
    url = api_url or settings.AUTH_API_URL

    username = username or settings.ADMIN_USER
    password = password or settings.ADMIN_PASSWORD

    if not username or not password:
        missing = [k for k, v in [("username", username), ("password", password)] if not v]
        click.echo(
            f"Error: {' and '.join(missing)} not provided. "
            f"Set them in .env.cli or pass --{'/--'.join(missing)}.",
            err=True,
        )
        raise click.Abort

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
