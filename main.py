"""Entry point for NexusWF automation tasks."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from browser.session import open_session
from config.settings import Settings
from pages.login import LoginPage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_login(settings: Settings, *, keep_open_seconds: int = 0) -> str:
    async with open_session(settings) as session:
        login_page = LoginPage(session.page, session.human, settings.base_url)

        logger.info("Opening login page at %s", login_page.login_url)
        await login_page.login(settings.username, settings.password)

        final_url = await login_page.wait_for_post_login()
        logger.info("Login succeeded — landed on %s", final_url)

        if keep_open_seconds > 0:
            logger.info("Keeping browser open for %d seconds", keep_open_seconds)
            await session.human.pause(keep_open_seconds * 1000, keep_open_seconds * 1000)

        return final_url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NexusWF browser automation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    login_parser = subparsers.add_parser("login", help="Log in to NexusWF")
    login_parser.add_argument(
        "--keep-open",
        type=int,
        default=5,
        metavar="SECONDS",
        help="Seconds to keep the browser open after login (default: 5, 0 to close immediately)",
    )

    args = parser.parse_args(argv)

    try:
        settings = Settings.load()
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    if args.command == "login":
        try:
            asyncio.run(run_login(settings, keep_open_seconds=args.keep_open))
        except RuntimeError as exc:
            logger.error("%s", exc)
            return 1
        except Exception:
            logger.exception("Login failed with an unexpected error")
            return 1
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
