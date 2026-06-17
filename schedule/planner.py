"""Distribute target duration across rows, breaks, and idle time."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from data.records import CaseRecord
from human.actor import HumanActor

if TYPE_CHECKING:
    from browser.control import RunControl

logger = logging.getLogger(__name__)

# Fixed per-action timings for copy-paste entry at pace 1.0 (seconds).
_ENTRY_START_THINK = 1.3
_BETWEEN_FIELD_PAUSE = 0.45
_PASTE_FIELD_SECONDS = 1.8
_SELECT_FIELD_SECONDS = 2.0
_PRE_SUBMIT_SECONDS = 2.0
_MIN_PACE = 0.30
_MAX_PACE = 1.15
# NexusWF clocks out after prolonged inactivity; never rest longer than this.
MAX_BREAK_SECONDS = 180


@dataclass(frozen=True)
class PlannedBreak:
    after_index: int
    duration_seconds: float


def clamp_break_seconds(duration_seconds: float) -> float:
    return min(duration_seconds, MAX_BREAK_SECONDS)


def plan_breaks(total_records: int, target_seconds: float, seed: int) -> list[PlannedBreak]:
    """Reserve spread-out rest periods; each pause is capped to avoid clock-out."""
    rng = random.Random(seed)
    count = rng.randint(5, 8)
    break_total = target_seconds * rng.uniform(0.10, 0.15)
    raw_each = break_total / count
    points = sorted(
        {max(0, min(total_records - 1, int(total_records * (i + 1) / (count + 1)) - 1)) for i in range(count)}
    )
    return [
        PlannedBreak(
            after_index=point,
            duration_seconds=clamp_break_seconds(raw_each * rng.uniform(0.85, 1.15)),
        )
        for point in points
    ]


def schedule_seed(task_file: str, target_seconds: float) -> int:
    return hash((task_file, round(target_seconds, 3))) & 0xFFFFFFFF


def estimate_entry_seconds(record: CaseRecord) -> float:
    """Estimate copy-paste entry duration at pace 1.0 (flat per field, not per character)."""
    text_fields = 4  # case_ref, client, jurisdiction, summary
    if record.record_source:
        text_fields += 1

    between_fields = text_fields + 3  # pauses between each step
    return (
        _ENTRY_START_THINK
        + text_fields * _PASTE_FIELD_SECONDS
        + 3 * _SELECT_FIELD_SECONDS
        + between_fields * _BETWEEN_FIELD_PAUSE
        + _PRE_SUBMIT_SECONDS
    )


class EntryScheduler:
    """Allocate wall-clock slots so row work plus planned breaks match the target."""

    def __init__(
        self,
        target_duration_seconds: float,
        total_records: int,
        completed_count: int,
        elapsed_seconds: float,
        planned_breaks: list[PlannedBreak],
    ) -> None:
        self.target_duration_seconds = target_duration_seconds
        self.total_records = total_records
        self.completed_count = completed_count
        self.elapsed_seconds = elapsed_seconds
        self.planned_breaks = planned_breaks

    @property
    def remaining_records(self) -> int:
        return max(0, self.total_records - self.completed_count)

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.target_duration_seconds - self.elapsed_seconds)

    def _future_break_seconds(self) -> float:
        return sum(
            clamp_break_seconds(break_.duration_seconds)
            for break_ in self.planned_breaks
            if break_.after_index >= self.completed_count
        )

    def next_slot_seconds(self) -> float:
        """Seconds allocated to the next record, excluding upcoming planned breaks."""
        if self.remaining_records <= 0:
            return 0.0

        work_remaining = self.remaining_seconds - self._future_break_seconds()
        work_remaining = max(0.0, work_remaining)
        base = work_remaining / self.remaining_records
        return base * random.uniform(0.94, 1.06)

    def entry_budget(self, slot_seconds: float) -> float:
        """Portion of the row slot spent on active form entry (rest is idle within slot)."""
        return slot_seconds * random.uniform(0.78, 0.88)

    def compute_pace(self, record: CaseRecord, entry_budget: float) -> float:
        """Scale human delays so natural entry fits the allotted entry budget."""
        natural = estimate_entry_seconds(record)
        if natural <= 0:
            return 1.0
        pace = entry_budget / natural
        return max(_MIN_PACE, min(_MAX_PACE, pace))

    def break_after(self, completed_index: int) -> PlannedBreak | None:
        for break_ in self.planned_breaks:
            if break_.after_index == completed_index:
                return break_
        return None

    def should_simulate_interruption(self) -> bool:
        return self.completed_count > 3 and random.random() < 0.03

    async def fill_to_slot(
        self,
        human: HumanActor,
        row_start: float,
        slot_seconds: float,
        control: RunControl | None = None,
    ) -> float:
        """Idle until the row slot elapses. Returns extra seconds waited."""
        padding_start = time.monotonic()

        while True:
            if control is not None:
                control.raise_if_stopped()

            elapsed = time.monotonic() - row_start
            remaining = slot_seconds - elapsed
            if remaining <= 0.2:
                break

            if remaining > 6:
                chunk = min(remaining - 0.3, random.uniform(2.0, 6.0))
                if random.random() < 0.2:
                    await human.scroll(direction=random.choice(["down", "up"]))
                else:
                    await human.think(chunk * 900, chunk * 1000)
            else:
                await asyncio.sleep(remaining)

        return time.monotonic() - padding_start

    async def take_break(
        self,
        human: HumanActor,
        duration_seconds: float,
        control: RunControl | None = None,
    ) -> float:
        """Pause up to MAX_BREAK_SECONDS; returns actual seconds rested."""
        duration = clamp_break_seconds(duration_seconds)
        if duration_seconds > MAX_BREAK_SECONDS:
            logger.info(
                "Capping break from %.0fs to %.0fs (inactivity clock-out limit)",
                duration_seconds,
                duration,
            )
        logger.info("Taking a scheduled break (%.0f seconds)", duration)
        remaining = duration
        while remaining > 1:
            if control is not None:
                control.raise_if_stopped()
            chunk = min(remaining, random.uniform(20, 45))
            await human.think(chunk * 950, chunk * 1000)
            remaining -= chunk
            if remaining > 30 and random.random() < 0.15:
                await human.scroll()
        return duration

    async def simulate_connection_blip(self) -> float:
        delay = random.uniform(20, 60)
        logger.warning("Connection seems slow — waiting %.0f seconds", delay)
        await asyncio.sleep(delay)
        return delay
