import asyncio
import json
import re

import aiohttp
import click

from .auth import ensure_token, make_cookie_header
from .config import get_cli_settings


def _parse_ids(value: str):
    """Parse comma or whitespace-separated IDs into a list of ints."""
    if not value:
        return []
    return [int(x) for x in re.split(r"[\s,]+", value) if x]


@click.command()
@click.option("--date", required=True, help="Dispatch date (YYYY-MM-DD)")
@click.option("--departure", "departure_raw", default="",
              help="Internal departure point IDs (comma or space-separated, e.g. '1,2,3')")
@click.option("--destination", "destination_raw", default="",
              help="Internal destination point IDs (comma or space-separated)")
@click.option("--departure-ext", "departure_ext_raw", default="",
              help="External departure point IDs (comma or space-separated)")
@click.option("--destination-ext", "destination_ext_raw", default="",
              help="External destination point IDs (comma or space-separated)")
@click.option("--weight", required=True, type=float, help="Cargo weight")
@click.option("--type", "container_type", required=True, type=int, help="Container size in feet (20 or 40)")
@click.option("--demo-uid", default=None, help="Demo user UID (uses X-Demo-User-UID header)")
@click.option("--api-url", default=None, help="API base URL override")
def route_query(
    date: str,
    departure_raw: str,
    destination_raw: str,
    departure_ext_raw: str,
    destination_ext_raw: str,
    weight: float,
    container_type: int,
    demo_uid: str | None,
    api_url: str | None,
):
    """Query route calculator and show results."""
    settings = get_cli_settings()
    url = f"{api_url or settings.API_BASE_URL}/v2/routes/calculate"

    departure_ids = _parse_ids(departure_raw)
    destination_ids = _parse_ids(destination_raw)
    departure_ext_ids = [x for x in departure_ext_raw.replace(",", " ").split() if x]
    destination_ext_ids = [x for x in destination_ext_raw.replace(",", " ").split() if x]

    payload = {
        "dispatchDate": date,
        "departureInternalIds": departure_ids,
        "destinationInternalIds": destination_ids,
        "departureExternalIds": departure_ext_ids,
        "destinationExternalIds": destination_ext_ids,
        "cargoWeight": weight,
        "containerType": container_type,
    }

    headers = {}
    if demo_uid:
        headers["X-Demo-User-UID"] = demo_uid
    else:
        token = ensure_token()
        headers.update(make_cookie_header(token))

    async def _request():
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, json=payload) as resp:
                body = await resp.json()
                return resp.status, body

    status, body = asyncio.run(_request())

    if status != 200:
        click.echo(f"Error (HTTP {status}):", err=True)

    click.echo(json.dumps(body, indent=2, ensure_ascii=False))
    if not body.get("routes") and not body.get("errors"):
        click.echo("No routes found, no errors reported.")
