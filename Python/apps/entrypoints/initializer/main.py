"""One-shot initializer entrypoint.

Runs the data initialization steps when the system starts.

Run as: python -m entrypoints.initializer.main
"""

import asyncio
import logging


async def main() -> None:
    """Run the initialization steps."""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
