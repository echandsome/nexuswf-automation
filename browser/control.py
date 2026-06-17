"""Cooperative stop signal for the automation workflow."""

from __future__ import annotations

import threading


class WorkflowStopped(Exception):
    """Raised when the user requests a stop from the UI."""


class RunControl:
    def __init__(self) -> None:
        self._stop = threading.Event()

    def request_stop(self) -> None:
        self._stop.set()

    def reset(self) -> None:
        self._stop.clear()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    def raise_if_stopped(self) -> None:
        if self.stopped:
            raise WorkflowStopped()
