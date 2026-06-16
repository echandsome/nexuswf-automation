"""Entry point for NexusWF automation tasks."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from browser.session import open_session
from browser.workflow import run_workflow
from config.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run(settings: Settings, *, keep_open_seconds: int = 0) -> None:
    async with open_session(settings) as session:
        downloaded = await run_workflow(session, settings)
        if downloaded:
            logger.info("Task file ready at %s", downloaded)
        else:
            logger.info("No new task file downloaded")

        if keep_open_seconds > 0:
            logger.info("Keeping browser open for %d seconds", keep_open_seconds)
            await session.human.pause(keep_open_seconds * 1000, keep_open_seconds * 1000)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="NexusWF automation: login, clock in, and download legal records task",
    )
    parser.add_argument(
        "--keep-open",
        type=int,
        default=5,
        metavar="SECONDS",
        help="Seconds to keep the browser open after completion (default: 5, 0 to close immediately)",
    )

    args = parser.parse_args(argv)

    try:
        settings = Settings.load()
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    try:
        asyncio.run(run(settings, keep_open_seconds=args.keep_open))
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    except Exception:
        logger.exception("Automation failed with an unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
