"""Employee dashboard interactions."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from pages.base import BasePage

logger = logging.getLogger(__name__)

_PORTAL_URL_PATTERN = re.compile(r"portal\.ilsl\.co\.uk/legal/files/records", re.I)


@dataclass(frozen=True)
class RecordsWorkSession:
    """Tab for legal records work and whether to clock out on the dashboard when done."""

    records_tab: Page
    clock_out_when_done: bool


class DashboardPage(BasePage):
    CLOCK_IN_BUTTON = "#clockBtn.clock-btn-in"
    CLOCK_OUT_BUTTON = "#clockBtn.clock-btn-out"

    async def reload(self) -> None:
        logger.info("Reloading employee dashboard")
        await self.page.reload(wait_until="domcontentloaded")
        await self.human.think(600, 1200)

    async def open_records_work_tab(self, portal_url: str) -> RecordsWorkSession:
        """
        Start the records work session.

        Clock In opens the portal in a new tab. If already clocked in (Clock Out
        shown), open the portal directly instead.
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
            logger.info("Already clocked in — opening records portal directly")
            records_tab = await self.page.context.new_page()
            await records_tab.goto(portal_url, wait_until="domcontentloaded")
            await records_tab.bring_to_front()
            await self.human.think(500, 1000)
            return RecordsWorkSession(records_tab=records_tab, clock_out_when_done=True)

        raise RuntimeError(
            "Neither Clock In nor Clock Out button is visible on the dashboard."
        )

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
        await self.page.bring_to_front()
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
