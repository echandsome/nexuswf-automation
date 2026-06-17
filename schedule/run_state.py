"""Persistent multi-task run state for resumable continuous processing."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_RUN_STATE_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunState:
    version: int = _RUN_STATE_VERSION
    started_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    completed_files: list[str] = field(default_factory=list)

    @property
    def completed_tasks(self) -> int:
        return len(self.completed_files)

    def is_counted(self, task_file: str) -> bool:
        return task_file in self.completed_files

    def mark_done(self, task_file: str) -> bool:
        """Record a fully-entered task. Returns True if newly counted."""
        if task_file in self.completed_files:
            return False
        self.completed_files.append(task_file)
        self.updated_at = _utc_now()
        return True


class RunStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> RunState:
        if not self.path.is_file():
            return RunState()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return RunState(
            version=raw.get("version", _RUN_STATE_VERSION),
            started_at=raw.get("started_at", _utc_now()),
            updated_at=raw.get("updated_at", _utc_now()),
            completed_files=list(raw.get("completed_files", [])),
        )

    def save(self, state: RunState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")
        temp.replace(self.path)
        logger.debug("Saved run state (%d tasks done)", state.completed_tasks)
