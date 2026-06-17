"""Legal records portal (ILSL) task page interactions."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from human.actor import HumanActor
from pages.base import BasePage

logger = logging.getLogger(__name__)

_PORTAL_URL_PATTERN = re.compile(r"portal\.ilsl\.co\.uk/legal/files/records", re.I)
USERNAME_INPUT = 'input[name="username"]'
PASSWORD_INPUT = 'input[name="password"]'
LOGIN_BUTTON = 'button[name="login"]'
DOWNLOAD_BUTTON = "#headerDownloadBtn"
TASK_FILENAME = "#headerTaskFilename"
REQUEST_TASK_BUTTON = "#requestTaskBtn"


class LegalRecordsPage(BasePage):
    @property
    def portal_url(self) -> str:
        return self.base_url

    def _on_portal_url(self) -> bool:
        return bool(_PORTAL_URL_PATTERN.search(self.page.url))

    async def is_login_page(self) -> bool:
        return await self.page.locator(USERNAME_INPUT).is_visible()

    async def is_task_page(self) -> bool:
        return await self.page.locator(DOWNLOAD_BUTTON).is_visible()

    async def ensure_on_portal(self) -> None:
        """Use the clock-in tab when it lands on the portal; otherwise open it directly."""
        if self._on_portal_url():
            logger.info("Using clock-in tab at %s", self.page.url)
            await self.page.wait_for_load_state("domcontentloaded")
        else:
            logger.info(
                "Clock-in tab is not on the records portal (%s) — opening %s",
                self.page.url,
                self.portal_url,
            )
            await self.page.goto(self.portal_url, wait_until="domcontentloaded")

        await self._wait_for_interactive_state()

    async def _wait_for_interactive_state(self, timeout_ms: int = 30_000) -> None:
        """Wait until either the login form or the download link is shown."""
        login = self.page.locator(USERNAME_INPUT)
        download = self.page.locator(DOWNLOAD_BUTTON)
        try:
            await login.or_(download).first.wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Legal records portal did not show a login form or task download link. "
                f"Current URL: {self.page.url}"
            ) from exc

        await self.human.think(400, 900)

    async def login(self, username: str, password: str) -> None:
        logger.info("Logging in to legal records portal")
        await self.page.locator(USERNAME_INPUT).wait_for(state="visible")
        await self.human.type_text(USERNAME_INPUT, username)
        await self.human.pause(350, 900)
        await self.human.type_text(PASSWORD_INPUT, password)
        await self.human.pause(400, 1000)
        await self.human.click(LOGIN_BUTTON)
        await self._wait_for_task_page()

    async def ensure_authenticated(self, username: str, password: str) -> None:
        """Log in only when the authorized-access form is shown."""
        if await self.page.locator("#mainRecordForm").is_visible():
            logger.info("Case entry form already open — ready to work")
            return

        if await self.is_login_page():
            await self.login(username, password)
            return

        await self.ensure_on_portal()

        if await self.is_login_page():
            await self.login(username, password)
            return

        if await self.is_task_page():
            logger.info("Already authenticated on legal records portal")
            return

        logger.info("Portal page not ready — reloading %s", self.portal_url)
        await self.page.goto(self.portal_url, wait_until="domcontentloaded")
        await self._wait_for_interactive_state()

        if await self.is_login_page():
            await self.login(username, password)
            return

        if await self.is_task_page():
            logger.info("Records page ready after reload")
            return

        raise RuntimeError(
            "Legal records page is neither the login form nor the task page. "
            f"Current URL: {self.page.url}"
        )

    async def _wait_for_task_page(self, timeout_ms: int = 30_000) -> None:
        try:
            await self.page.locator(DOWNLOAD_BUTTON).wait_for(
                state="visible",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Legal records login did not reach the task page within the timeout. "
                "Check credentials or look for an error message on the page."
            ) from exc

        await self.human.think(600, 1400)

    async def download_task_if_needed(self, downloads_dir: Path) -> Path | None:
        """Download the task spreadsheet when a download link is present."""
        download_btn = self.page.locator(DOWNLOAD_BUTTON)
        try:
            await download_btn.wait_for(state="visible", timeout=15_000)
        except PlaywrightTimeoutError:
            logger.info("No task download link visible — skipping download")
            return None

        filename_el = self.page.locator(TASK_FILENAME)
        filename = (await filename_el.inner_text()).strip() if await filename_el.count() else ""
        if not filename:
            filename = await download_btn.get_attribute("download") or "legal_records_task.xlsx"

        dest = downloads_dir / filename
        if dest.exists():
            logger.info("Task file already downloaded: %s", dest)
            return dest

        logger.info("Downloading task file: %s", filename)
        async with self.page.expect_download() as download_info:
            await self.human.click(DOWNLOAD_BUTTON)

        download = await download_info.value
        await download.save_as(dest)
        logger.info("Saved task file to %s", dest)
        return dest

    async def current_task_filename(self) -> str:
        filename_el = self.page.locator(TASK_FILENAME)
        if await filename_el.count():
            return (await filename_el.inner_text()).strip()
        return ""

    async def request_new_task(self, previous_filename: str = "") -> None:
        """Click "Request New Task" and wait for a fresh dataset to be offered."""
        logger.info("Requesting a new task (previous: %s)", previous_filename or "n/a")
        await self.human.think(800, 1800)
        await self.human.click(REQUEST_TASK_BUTTON)

        try:
            await self.page.wait_for_function(
                """([sel, prev]) => {
                    const el = document.querySelector(sel);
                    if (!el) return false;
                    const text = el.innerText.trim();
                    return text.length > 0 && text !== prev;
                }""",
                arg=[TASK_FILENAME, previous_filename],
                timeout=120_000,
            )
        except PlaywrightTimeoutError:
            logger.warning(
                "Task filename did not change after requesting a new task — "
                "waiting for the download link instead"
            )
            await self.page.locator(DOWNLOAD_BUTTON).wait_for(
                state="visible", timeout=30_000
            )

        await self.human.think(600, 1400)
        logger.info("New task ready: %s", await self.current_task_filename())

    async def request_and_download_new_task(
        self, downloads_dir: Path, previous_filename: str = ""
    ) -> Path | None:
        # Prefer the filename currently shown on the portal to detect the change.
        displayed = await self.current_task_filename()
        await self.request_new_task(displayed or previous_filename)
        return await self.download_task_if_needed(downloads_dir)


def legal_records_page(page: Page, human: HumanActor, portal_url: str) -> LegalRecordsPage:
    return LegalRecordsPage(page, human, portal_url)
