"""Employee dashboard interactions."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from pages.base import BasePage

logger = logging.getLogger(__name__)

_PORTAL_URL_PATTERN = re.compile(r"portal\.ilsl\.co\.uk/legal/files/records", re.I)
_ENTRY_URL_PATTERN = re.compile(r"/entry", re.I)


@dataclass(frozen=True)
class RecordsWorkSession:
    """Tab for legal records work and whether to clock out when the session ends."""

    records_tab: Page
    clock_out_when_done: bool


class DashboardPage(BasePage):
    CLOCK_IN_BUTTON = "#clockBtn.clock-btn-in"
    CLOCK_OUT_BUTTON = "#clockBtn.clock-btn-out"

    @property
    def dashboard_url(self) -> str:
        return f"{self.base_url}/employee-dashboard"

    async def go_to_dashboard(self) -> None:
        if "employee-dashboard" not in self.page.url:
            logger.info("Opening employee dashboard")
            await self.page.goto(self.dashboard_url, wait_until="domcontentloaded")
        await self.page.bring_to_front()

    async def reload(self) -> None:
        logger.info("Reloading employee dashboard")
        await self.page.reload(wait_until="domcontentloaded")
        await self.human.think(600, 1200)

    async def is_clocked_in(self) -> bool:
        clock_out = self.page.locator(self.CLOCK_OUT_BUTTON)
        try:
            await clock_out.wait_for(state="visible", timeout=5_000)
            return True
        except PlaywrightTimeoutError:
            return False

    @staticmethod
    def find_existing_records_tab(context: BrowserContext) -> Page | None:
        """Return an open portal or entry tab if the user is already working."""
        for page in context.pages:
            url = page.url
            if _PORTAL_URL_PATTERN.search(url) or _ENTRY_URL_PATTERN.search(url):
                return page
        return None

    async def open_records_work_tab(
        self,
        portal_url: str,
        *,
        entry_url: str | None = None,
        resume_entry: bool = False,
    ) -> RecordsWorkSession:
        """
        Start the records work session.

        Clock In opens the portal in a new tab. If already clocked in, reuse an
        existing portal tab when possible and go straight to the task or entry page.
        """
        clock_in = self.page.locator(self.CLOCK_IN_BUTTON)
        clock_out = self.page.locator(self.CLOCK_OUT_BUTTON)

        try:
            await clock_in.or_(clock_out).first.wait_for(state="visible", timeout=15_000)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Neither Clock In nor Clock Out button found on the dashboard."
            ) from exc

        if await clock_in.is_visible():
            records_tab = await self._click_clock_in()
            return RecordsWorkSession(records_tab=records_tab, clock_out_when_done=True)

        if await clock_out.is_visible():
            return await self._open_when_already_clocked_in(
                portal_url,
                entry_url=entry_url,
                resume_entry=resume_entry,
            )

        raise RuntimeError(
            "Neither Clock In nor Clock Out button is visible on the dashboard."
        )

    async def _open_when_already_clocked_in(
        self,
        portal_url: str,
        *,
        entry_url: str | None,
        resume_entry: bool,
    ) -> RecordsWorkSession:
        logger.info("Already clocked in — opening records work directly")
        existing = self.find_existing_records_tab(self.page.context)
        if existing is not None:
            records_tab = existing
            logger.info("Reusing existing portal tab at %s", records_tab.url)
        else:
            records_tab = await self.page.context.new_page()
            logger.info("No portal tab open — opening records portal")

        await records_tab.bring_to_front()

        target = entry_url if resume_entry and entry_url else portal_url
        if resume_entry and entry_url:
            logger.info("Going directly to entry form to begin work")
        else:
            logger.info("Going to records task page")

        if not _PORTAL_URL_PATTERN.search(records_tab.url) and not (
            entry_url and _ENTRY_URL_PATTERN.search(records_tab.url)
        ):
            await records_tab.goto(target, wait_until="domcontentloaded")
        elif resume_entry and entry_url and not await records_tab.locator(
            "#mainRecordForm"
        ).is_visible():
            await records_tab.goto(entry_url, wait_until="domcontentloaded")

        await self.human.think(300, 700)
        return RecordsWorkSession(records_tab=records_tab, clock_out_when_done=False)

    async def _click_clock_in(self) -> Page:
        """Click Clock In and return the new tab that opens."""
        logger.info("Clicking Clock In")
        async with self.page.context.expect_page() as new_page_info:
            await self.human.click(self.CLOCK_IN_BUTTON)

        new_page = await new_page_info.value
        await new_page.bring_to_front()

        try:
            await new_page.wait_for_url(_PORTAL_URL_PATTERN, timeout=20_000)
            logger.info("Clock-in opened records portal tab: %s", new_page.url)
        except PlaywrightTimeoutError:
            logger.warning(
                "Clock-in tab did not navigate to the records portal (at %s); "
                "the workflow will open the portal on this tab",
                new_page.url,
            )

        await new_page.wait_for_load_state("domcontentloaded")
        await self.human.think(500, 1000)
        return new_page

    async def click_clock_out(self) -> None:
        """Clock out on the employee dashboard before ending the session."""
        await self.go_to_dashboard()
        clock_out = self.page.locator(self.CLOCK_OUT_BUTTON)
        try:
            await clock_out.wait_for(state="visible", timeout=15_000)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Clock Out button not found on the dashboard. "
                "You may already be clocked out."
            ) from exc

        logger.info("Clicking Clock Out")
        await self.human.click(self.CLOCK_OUT_BUTTON)
        await self.human.think(600, 1200)

        clock_in = self.page.locator(self.CLOCK_IN_BUTTON)
        try:
            await clock_in.wait_for(state="visible", timeout=10_000)
            logger.info("Clocked out successfully")
        except PlaywrightTimeoutError:
            logger.warning("Clock Out clicked but Clock In button did not appear")

    async def try_clock_out(self) -> bool:
        """Clock out when the session is active; return False if already clocked out."""
        await self.go_to_dashboard()
        if not await self.is_clocked_in():
            logger.info("Already clocked out")
            return False
        await self.click_clock_out()
        return True
