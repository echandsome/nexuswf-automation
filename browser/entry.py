"""Record entry loop with human pacing and resumable progress."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from playwright.async_api import Page

from config.settings import Settings
from data.records import CaseRecord, load_task_file
from human.actor import HumanActor
from pages.case_entry import CaseEntryPage
from schedule.planner import EntryScheduler
from schedule.progress import EntryProgress, ProgressStore

logger = logging.getLogger(__name__)


async def run_record_entry(
    page: Page,
    human: HumanActor,
    settings: Settings,
    task_file: Path,
) -> EntryProgress:
    records = load_task_file(task_file)
    store = ProgressStore(settings.entry_progress_path)
    progress = store.init_or_resume(
        task_file, settings.entry_duration_seconds, len(records)
    )

    if progress.is_done(len(records)):
        logger.info("All %d records already entered — nothing to do", len(records))
        return progress

    entry = CaseEntryPage(page, human, settings.ilsl_entry_url)
    await entry.open(settings.ilsl_entry_url)

    pending = [r for r in records if r.index not in progress.completed_indices]
    remaining_seconds = max(
        0.0, progress.target_duration_seconds - progress.elapsed_seconds
    )
    logger.info(
        "%d of %d records remaining over %.2f h remaining (~%.1fs/row), "
        "%.2f h already elapsed of %.2f h target",
        len(pending),
        len(records),
        remaining_seconds / 3600,
        remaining_seconds / len(pending) if pending else 0.0,
        progress.elapsed_seconds / 3600,
        progress.target_duration_seconds / 3600,
    )

    for record in pending:
        await _enter_one_record(entry, human, settings, store, progress, record, len(records))

    logger.info(
        "Record entry complete — %d records in %.0f minutes (target %.0f minutes)",
        progress.completed_count,
        progress.elapsed_seconds / 60,
        progress.target_duration_seconds / 60,
    )
    return progress


async def _enter_one_record(
    entry: CaseEntryPage,
    human: HumanActor,
    settings: Settings,
    store: ProgressStore,
    progress: EntryProgress,
    record: CaseRecord,
    total_records: int,
) -> None:
    scheduler = EntryScheduler(
        progress.target_duration_seconds,
        total_records,
        progress.completed_count,
        progress.elapsed_seconds,
        progress.planned_breaks,
    )
    slot_seconds = scheduler.next_slot_seconds()
    entry_budget = scheduler.entry_budget(slot_seconds)
    pace = scheduler.compute_pace(record, settings.file_executor, entry_budget)

    row_start = time.monotonic()

    if scheduler.should_simulate_interruption():
        blip_seconds = await scheduler.simulate_connection_blip()
        progress.log_interruption("connection_blip", blip_seconds)
        store.save(progress)
        await entry.recover_after_interruption(settings.ilsl_entry_url)
        row_start = time.monotonic()

    human.set_pace(pace)
    try:
        await entry.enter_record(record, settings.file_executor)
    finally:
        human.reset_pace()

    await scheduler.fill_to_slot(human, row_start, slot_seconds)
    total_row_seconds = time.monotonic() - row_start

    progress.mark_completed(record.index, record.case_ref, total_row_seconds)
    store.save(progress)

    logger.info(
        "Saved record %d/%d (%s) — slot %.0fs (pace %.2f), %.0f%% of target elapsed",
        progress.completed_count,
        total_records,
        record.case_ref,
        total_row_seconds,
        pace,
        100 * progress.elapsed_seconds / progress.target_duration_seconds,
    )

    scheduled_break = scheduler.break_after(record.index)
    if scheduled_break:
        break_seconds = await scheduler.take_break(
            human, scheduled_break.duration_seconds
        )
        progress.log_interruption("scheduled_break", break_seconds, detail="planned")
        store.save(progress)
        logger.info(
            "Break complete (%.0fs) — %.0f%% of target elapsed",
            break_seconds,
            100 * progress.elapsed_seconds / progress.target_duration_seconds,
        )
