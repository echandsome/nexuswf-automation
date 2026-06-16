"""Entry point for NexusWF automation tasks."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from browser.session import open_session
from browser.workflow import run_workflow
from config.settings import MIN_ENTRY_DURATION_HOURS, Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run(settings: Settings, *, keep_open_seconds: int = 0) -> None:
    async with open_session(settings) as session:
        task_file = await run_workflow(session, settings)
        if task_file:
            logger.info("Task file: %s", task_file)
        else:
            logger.info("Workflow finished without a task file")

        if keep_open_seconds > 0:
            logger.info("Keeping browser open for %d seconds", keep_open_seconds)
            await session.human.pause(keep_open_seconds * 1000, keep_open_seconds * 1000)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "NexusWF automation: login, clock in, download legal records, "
            "and enter rows at a human pace"
        ),
    )
    parser.add_argument(
        "--keep-open",
        type=int,
        default=5,
        metavar="SECONDS",
        help="Seconds to keep the browser open after completion (default: 5, 0 to close immediately)",
    )
    parser.add_argument(
        "--duration-hours",
        type=float,
        default=None,
        metavar="HOURS",
        help=(
            f"Total wall-clock time for entering all records, including breaks "
            f"(minimum {MIN_ENTRY_DURATION_HOURS}, default from ENTRY_DURATION_HOURS)"
        ),
    )

    args = parser.parse_args(argv)

    try:
        settings = Settings.load()
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    if args.duration_hours is not None:
        if args.duration_hours < MIN_ENTRY_DURATION_HOURS:
            logger.error(
                "--duration-hours must be at least %.1f (got %.2f)",
                MIN_ENTRY_DURATION_HOURS,
                args.duration_hours,
            )
            return 1
        from dataclasses import replace

        settings = replace(settings, entry_duration_hours=args.duration_hours)

    logger.info(
        "Target entry duration: %.1f hours",
        settings.entry_duration_hours,
    )

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
