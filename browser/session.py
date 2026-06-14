"""Browser lifecycle management with realistic fingerprint defaults."""

from __future__ import annotations

import random
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from config.settings import Settings
from human.actor import HumanActor

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

    async def close(self) -> None:
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()


@asynccontextmanager
async def open_session(settings: Settings) -> AsyncIterator[BrowserSession]:
    """Launch a browser, open a page, and yield a session with a HumanActor."""
    playwright = await async_playwright().start()

    launch_kwargs: dict = {
        "headless": settings.headless,
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    if settings.browser_channel:
        launch_kwargs["channel"] = settings.browser_channel

    browser = await playwright.chromium.launch(**launch_kwargs)

    viewport = random.choice(_VIEWPORTS)
    context = await browser.new_context(
        viewport=viewport,
        locale="en-US",
        timezone_id="America/New_York",
        accept_downloads=True,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
    )
    context.set_default_timeout(settings.default_timeout_ms)

    page = await context.new_page()
    human = HumanActor(page)

    session = BrowserSession(
        playwright=playwright,
        browser=browser,
        context=context,
        page=page,
        human=human,
    )

    try:
        yield session
    finally:
        await session.close()
