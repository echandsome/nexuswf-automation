"""End-to-end automation: login → clock in → (download → enter → request new task)*."""

from __future__ import annotations

import logging
from pathlib import Path

from browser.auth import ensure_logged_in
from browser.control import RunControl, WorkflowStopped
from browser.entry import run_record_entry
from browser.session import BrowserSession
from config.settings import Settings
from data.records import load_task_file
from human.actor import HumanActor
from pages.dashboard import DashboardPage
from pages.legal_records import LegalRecordsPage, legal_records_page
from schedule.progress import ProgressStore

logger = logging.getLogger(__name__)


async def run_workflow(
    session: BrowserSession,
    settings: Settings,
    control: RunControl | None = None,
) -> Path | None:
    await ensure_logged_in(session, settings)

    dashboard = DashboardPage(session.page, session.human, settings.base_url)
    target_tasks = settings.task_count if settings.continuous_mode else 1
    completed_tasks = 0
    resume_entry = _should_go_directly_to_entry(settings, completed_tasks)

    already_clocked_in = await dashboard.is_clocked_in()
    if already_clocked_in:
        logger.info("Already clocked in — continuing without dashboard reload")
    else:
        await dashboard.reload()

    work = await dashboard.open_records_work_tab(
        settings.ilsl_portal_url,
        entry_url=settings.ilsl_entry_url,
        resume_entry=resume_entry,
    )

    records_human = HumanActor(work.records_tab)
    records = legal_records_page(work.records_tab, records_human, settings.ilsl_portal_url)
    await records.ensure_authenticated(settings.ilsl_username, settings.ilsl_password)

    logger.info(
        "This run will process %d task(s)%s",
        target_tasks,
        " [continuous mode]" if settings.continuous_mode else "",
    )

    last_task_file: Path | None = None

    try:
        while completed_tasks < target_tasks:
            if control is not None:
                control.raise_if_stopped()

            task_number = completed_tasks + 1
            logger.info("=== Starting task %d of %d ===", task_number, target_tasks)

            task_file = await _resolve_task_file(
                records,
                settings,
                completed_tasks=completed_tasks,
                last_task_file=last_task_file,
            )
            if task_file is None:
                logger.error("No task file available for task %d — stopping", task_number)
                break

            progress = await run_record_entry(
                work.records_tab,
                records_human,
                settings,
                task_file,
                control,
            )
            record_count = _record_count(task_file)

            if control is not None and control.stopped:
                logger.info("Stop requested — ending after current work")
                last_task_file = task_file
                break

            if not progress.is_done(record_count):
                logger.warning(
                    "Task %d did not fully complete (%d/%d) — stopping loop",
                    task_number,
                    progress.completed_count,
                    record_count,
                )
                last_task_file = task_file
                break

            completed_tasks += 1
            last_task_file = task_file

            logger.info(
                "=== Task %d complete (%d of %d) — %.2f h, %d records ===",
                task_number,
                completed_tasks,
                target_tasks,
                progress.elapsed_seconds / 3600,
                progress.completed_count,
            )

        if control is None or not control.stopped:
            logger.info(
                "Run finished — %d of %d task(s) completed this session",
                completed_tasks,
                target_tasks,
            )
    except WorkflowStopped:
        logger.info("Stop requested — winding down")
        raise
    finally:
        stopped = control is not None and control.stopped
        if stopped:
            logger.info("Stop requested — clocking out")
            try:
                await dashboard.try_clock_out()
            except Exception:
                logger.warning("Clock out during stop failed", exc_info=True)
        elif work.clock_out_when_done:
            logger.info("Clocking out")
            await dashboard.click_clock_out()

    return last_task_file


def _should_go_directly_to_entry(settings: Settings, completed_tasks: int) -> bool:
    """Skip the portal task page and open the entry form when work can begin."""
    if _has_in_flight_progress(settings):
        return True
    if completed_tasks > 0:
        return False
    return _find_latest_task_file(settings.downloads_dir) is not None


def _has_in_flight_progress(settings: Settings) -> bool:
    progress = ProgressStore(settings.entry_progress_path).load()
    if not progress:
        return False
    task_file = Path(progress.task_file)
    if not task_file.is_file():
        return False
    records = load_task_file(task_file)
    return not progress.is_done(len(records))


async def _resolve_task_file(
    records: LegalRecordsPage,
    settings: Settings,
    *,
    completed_tasks: int,
    last_task_file: Path | None,
) -> Path | None:
    """Pick the task file for the current session, resuming or requesting as needed."""
    progress = ProgressStore(settings.entry_progress_path).load()

    if progress:
        in_flight = Path(progress.task_file)
        if in_flight.is_file() and not progress.is_done(_record_count(in_flight)):
            logger.info("Resuming in-flight task file: %s", in_flight.name)
            return in_flight

    if completed_tasks == 0:
        task_file = await records.download_task_if_needed(settings.downloads_dir)
        if task_file is None:
            task_file = _find_latest_task_file(settings.downloads_dir)
            if task_file:
                logger.info("Using existing task file: %s", task_file.name)
        return task_file

    previous_name = last_task_file.name if last_task_file else ""
    return await records.request_and_download_new_task(
        settings.downloads_dir, previous_filename=previous_name
    )


def _find_latest_task_file(downloads_dir: Path) -> Path | None:
    candidates = sorted(
        downloads_dir.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return candidates[0] if candidates else None


def _record_count(task_file: Path) -> int:
    return len(load_task_file(task_file))
