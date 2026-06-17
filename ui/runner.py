"""Run automation in a background thread with log capture."""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from typing import TYPE_CHECKING

from browser.control import RunControl, WorkflowStopped
from browser.session import open_session
from browser.workflow import run_workflow

if TYPE_CHECKING:
    from config.settings import Settings

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
_LOG_DATEFMT = "%H:%M:%S"


class _QueueHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue[str]) -> None:
        super().__init__()
        self._log_queue = log_queue
        self.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT))

    def emit(self, record: logging.LogRecord) -> None:
        self._log_queue.put(self.format(record))


class AutomationRunner:
    """Starts and stops the Playwright workflow on a worker thread."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.status = "idle"
        self.error: str | None = None
        self._handler: _QueueHandler | None = None
        self.control = RunControl()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, settings: Settings) -> None:
        if self.is_running():
            return
        self.error = None
        self.status = "running"
        self.control.reset()
        self._attach_logging()
        self._thread = threading.Thread(
            target=self._worker,
            args=(settings,),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if not self.is_running():
            return
        self.control.request_stop()
        logging.getLogger(__name__).info("Stop requested — will clock out and close")

    def _attach_logging(self) -> None:
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        if self._handler is None:
            self._handler = _QueueHandler(self.log_queue)
            root.addHandler(self._handler)

    def _worker(self, settings: Settings) -> None:
        try:
            asyncio.run(self._run(settings))
            self.status = "stopped" if self.control.stopped else "completed"
        except WorkflowStopped:
            self.status = "stopped"
        except Exception as exc:
            self.error = str(exc)
            self.status = "error"
            logging.getLogger(__name__).exception("Automation failed")

    async def _run(self, settings: Settings) -> None:
        try:
            async with open_session(settings) as session:
                try:
                    task_file = await run_workflow(session, settings, self.control)
                except WorkflowStopped:
                    logging.getLogger(__name__).info("Run stopped by user")
                    return

                if self.control.stopped:
                    return

                if task_file:
                    logging.getLogger(__name__).info("Task file: %s", task_file)
                else:
                    logging.getLogger(__name__).info("Workflow finished without a task file")

                if settings.keep_open_seconds > 0:
                    logging.getLogger(__name__).info(
                        "Keeping browser open for %d seconds", settings.keep_open_seconds
                    )
                    await session.human.pause(
                        settings.keep_open_seconds * 1000,
                        settings.keep_open_seconds * 1000,
                    )
        finally:
            if self.control.stopped:
                logging.getLogger(__name__).info("Automation stopped — browser closed")

    def drain_logs(self) -> list[str]:
        lines: list[str] = []
        while True:
            try:
                lines.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
        return lines
