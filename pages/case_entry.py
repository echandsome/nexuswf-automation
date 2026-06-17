"""Legal case entry form interactions."""

from __future__ import annotations

import logging

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from data.records import CaseRecord
from human.actor import HumanActor
from pages.base import BasePage

logger = logging.getLogger(__name__)

FORM = "#mainRecordForm"
CASE_REF = "#c_ref"
CLIENT_NAME = "#c_client"
CASE_TYPE = "#c_type"
JURISDICTION = "#c_jur"
RECORD_SOURCE = "#c_source"
DOCUMENT_STATUS = "#c_doc_status"
CASE_STATUS = "#c_status"
CASE_SUMMARY = "#c_summary"
SUBMIT_BUTTON = "#submitActionBtn"


class CaseEntryPage(BasePage):
    async def open(self, entry_url: str) -> None:
        if await self.page.locator(FORM).is_visible():
            logger.info("Case entry form already open")
            return

        logger.info("Opening case entry form at %s", entry_url)
        await self.page.goto(entry_url, wait_until="domcontentloaded")
        await self._wait_for_form()

    async def _wait_for_form(self, timeout_ms: int = 30_000) -> None:
        try:
            await self.page.locator(FORM).wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Case entry form did not appear. "
                f"Current URL: {self.page.url}"
            ) from exc
        await self.human.think(500, 1200)

    async def recover_after_interruption(self, entry_url: str) -> None:
        logger.info("Reloading case entry page after interruption")
        await self.page.reload(wait_until="domcontentloaded")
        try:
            await self._wait_for_form()
        except RuntimeError:
            await self.page.goto(entry_url, wait_until="domcontentloaded")
            await self._wait_for_form()

    async def enter_record(self, record: CaseRecord) -> None:
        logger.info(
            "Entering record %d/%s — %s",
            record.index + 1,
            record.case_ref,
            record.client_name,
        )

        await self.human.think(800, 1800)
        await self.human.paste_text(CASE_REF, record.case_ref)
        await self.human.pause(250, 700)
        await self.human.paste_text(CLIENT_NAME, record.client_name)
        await self.human.pause(300, 800)
        await self.human.select_option(CASE_TYPE, record.case_type_value)
        await self.human.pause(250, 650)
        await self.human.paste_text(JURISDICTION, record.jurisdiction)
        await self.human.pause(200, 600)

        if record.record_source:
            await self.human.paste_text(RECORD_SOURCE, record.record_source)
            await self.human.pause(200, 550)

        await self.human.select_option(DOCUMENT_STATUS, record.document_status)
        await self.human.pause(200, 550)
        await self.human.select_option(CASE_STATUS, record.case_status)
        await self.human.pause(400, 1000)
        await self.human.scroll(direction="down")
        await self.human.think(600, 1400)
        await self.human.paste_text(CASE_SUMMARY, record.case_summary)
        await self.human.think(500, 1200)
        await self.human.click(SUBMIT_BUTTON)
        await self._wait_for_submit_complete()

    async def _wait_for_submit_complete(self, timeout_ms: int = 20_000) -> None:
        try:
            await self.page.locator(FORM).wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Case entry form did not return after submit. "
                f"Current URL: {self.page.url}"
            ) from exc
        await self.human.think(700, 1500)


def case_entry_page(page, human: HumanActor, base_url: str) -> CaseEntryPage:
    return CaseEntryPage(page, human, base_url)
