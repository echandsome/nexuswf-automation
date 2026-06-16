"""Persistent progress for resumable record entry."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from schedule.planner import PlannedBreak, plan_breaks, schedule_seed

logger = logging.getLogger(__name__)

_PROGRESS_VERSION = 2


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CompletedEntry:
    index: int
    case_ref: str
    completed_at: str
    duration_seconds: float


@dataclass
class EntryProgress:
    version: int
    task_file: str
    target_duration_seconds: float
    started_at: str
    updated_at: str
    planned_breaks: list[PlannedBreak]
    completed: list[CompletedEntry] = field(default_factory=list)
    interruptions: list[dict] = field(default_factory=list)

    @property
    def completed_indices(self) -> set[int]:
        return {entry.index for entry in self.completed}

    @property
    def completed_count(self) -> int:
        return len(self.completed)

    @property
    def entry_seconds(self) -> float:
        return sum(entry.duration_seconds for entry in self.completed)

    @property
    def break_seconds(self) -> float:
        return sum(item["duration_seconds"] for item in self.interruptions)

    @property
    def elapsed_seconds(self) -> float:
        return self.entry_seconds + self.break_seconds

    def is_done(self, total_records: int) -> bool:
        return self.completed_count >= total_records

    def mark_completed(self, index: int, case_ref: str, duration_seconds: float) -> None:
        self.completed.append(
            CompletedEntry(
                index=index,
                case_ref=case_ref,
                completed_at=_utc_now(),
                duration_seconds=round(duration_seconds, 2),
            )
        )
        self.updated_at = _utc_now()

    def log_interruption(self, kind: str, duration_seconds: float, detail: str = "") -> None:
        self.interruptions.append(
            {
                "at": _utc_now(),
                "kind": kind,
                "duration_seconds": round(duration_seconds, 2),
                "detail": detail,
            }
        )
        self.updated_at = _utc_now()


class ProgressStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> EntryProgress | None:
        if not self.path.is_file():
            return None

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        completed = [CompletedEntry(**item) for item in raw.get("completed", [])]
        planned_breaks = [
            PlannedBreak(**item) for item in raw.get("planned_breaks", [])
        ]
        return EntryProgress(
            version=raw.get("version", _PROGRESS_VERSION),
            task_file=raw["task_file"],
            target_duration_seconds=float(raw["target_duration_seconds"]),
            started_at=raw["started_at"],
            updated_at=raw["updated_at"],
            planned_breaks=planned_breaks,
            completed=completed,
            interruptions=raw.get("interruptions", []),
        )

    def save(self, progress: EntryProgress) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(progress)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp.replace(self.path)
        logger.debug("Saved entry progress (%d records)", progress.completed_count)

    def init_or_resume(
        self,
        task_file: Path,
        target_duration_seconds: float,
        total_records: int,
    ) -> EntryProgress:
        existing = self.load()
        task_key = str(task_file.resolve())
        seed = schedule_seed(task_key, target_duration_seconds)

        if existing and existing.task_file == task_key:
            if not existing.planned_breaks:
                existing.planned_breaks = plan_breaks(
                    total_records, existing.target_duration_seconds, seed
                )
                self.save(existing)
            logger.info(
                "Resuming entry progress: %d completed, %.0fs / %.0fs elapsed "
                "(avg %.1fs/row, target avg %.1fs/row)",
                existing.completed_count,
                existing.elapsed_seconds,
                existing.target_duration_seconds,
                existing.entry_seconds / max(existing.completed_count, 1),
                (existing.target_duration_seconds - sum(b.duration_seconds for b in existing.planned_breaks))
                / total_records,
            )
            return existing

        if existing and existing.task_file != task_key:
            logger.warning(
                "Task file changed — starting fresh progress (was %s, now %s)",
                existing.task_file,
                task_key,
            )

        breaks = plan_breaks(total_records, target_duration_seconds, seed)
        break_total = sum(b.duration_seconds for b in breaks)
        work_per_row = (target_duration_seconds - break_total) / total_records

        now = _utc_now()
        progress = EntryProgress(
            version=_PROGRESS_VERSION,
            task_file=task_key,
            target_duration_seconds=target_duration_seconds,
            started_at=now,
            updated_at=now,
            planned_breaks=breaks,
        )
        self.save(progress)
        logger.info(
            "Started new entry run: %d records, %.1f hours total, "
            "%.0f min breaks, ~%.1fs per record",
            total_records,
            target_duration_seconds / 3600,
            break_total / 60,
            work_per_row,
        )
        return progress
