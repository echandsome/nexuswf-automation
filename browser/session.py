"""Browser lifecycle management with realistic fingerprint defaults."""

from __future__ import annotations

import logging
import random
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from browser.storage import save_storage_state, storage_state_for_context
from config.settings import Settings
from human.actor import HumanActor

logger = logging.getLogger(__name__)

_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
]


@dataclass
class BrowserSession:
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page
    human: HumanActor
    settings: Settings

    async def close(self) -> None:
        await save_storage_state(self.context, self.settings.storage_state_path)
        logger.info("Saved browser session to %s", self.settings.storage_state_path)
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()


@asynccontextmanager
async def open_session(settings: Settings) -> AsyncIterator[BrowserSession]:
    """Launch a browser, restore saved state if present, and save on close."""
    playwright = await async_playwright().start()

    launch_kwargs: dict = {
        "headless": settings.headless,
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    if settings.browser_channel:
        launch_kwargs["channel"] = settings.browser_channel

    browser = await playwright.chromium.launch(**launch_kwargs)

    viewport = random.choice(_VIEWPORTS)
    context_kwargs: dict = {
        "viewport": viewport,
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "accept_downloads": True,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
    }
    saved_state = storage_state_for_context(settings.storage_state_path)
    if saved_state:
        context_kwargs.update(saved_state)
        logger.info("Restored browser session from %s", settings.storage_state_path)

    context = await browser.new_context(**context_kwargs)
    context.set_default_timeout(settings.default_timeout_ms)

    page = await context.new_page()
    human = HumanActor(page)

    session = BrowserSession(
        playwright=playwright,
        browser=browser,
        context=context,
        page=page,
        human=human,
        settings=settings,
    )

    try:
        yield session
    finally:
        await session.close()
