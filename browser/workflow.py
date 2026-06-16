"""End-to-end automation: login → clock in → download task → enter records."""

from __future__ import annotations

import logging
from pathlib import Path

from browser.auth import ensure_logged_in
from browser.entry import run_record_entry
from browser.session import BrowserSession
from config.settings import Settings
from human.actor import HumanActor
from pages.dashboard import DashboardPage
from pages.legal_records import legal_records_page

logger = logging.getLogger(__name__)


async def run_workflow(session: BrowserSession, settings: Settings) -> Path | None:
    await ensure_logged_in(session, settings)

    dashboard = DashboardPage(session.page, session.human, settings.base_url)
    await dashboard.reload()

    work = await dashboard.open_records_work_tab(settings.ilsl_portal_url)

    records_human = HumanActor(work.records_tab)
    records = legal_records_page(work.records_tab, records_human, settings.ilsl_portal_url)
    await records.ensure_authenticated(settings.ilsl_username, settings.ilsl_password)
    task_file = await records.download_task_if_needed(settings.downloads_dir)

    if task_file is None:
        task_file = _find_latest_task_file(settings.downloads_dir)
        if task_file is None:
            logger.error("No task file available to enter records")
            return None
        logger.info("Using existing task file: %s", task_file)

    progress = await run_record_entry(work.records_tab, records_human, settings, task_file)
    logger.info(
        "Entry session finished: %d records, %.1f / %.1f hours",
        progress.completed_count,
        progress.elapsed_seconds / 3600,
        progress.target_duration_seconds / 3600,
    )

    if work.clock_out_when_done and progress.is_done(_record_count(task_file)):
        await dashboard.click_clock_out()

    return task_file


def _find_latest_task_file(downloads_dir: Path) -> Path | None:
    candidates = sorted(downloads_dir.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _record_count(task_file: Path) -> int:
    from data.records import load_task_file

    return len(load_task_file(task_file))
