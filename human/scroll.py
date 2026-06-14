"""Natural scrolling behavior."""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

from human.delays import pause

if TYPE_CHECKING:
    from playwright.async_api import Page


async def scroll_page(page: Page, *, direction: str = "down", amount: int | None = None) -> None:
    """Scroll the page in small increments with pauses between steps."""
    delta = amount or random.randint(120, 320)
    if direction == "up":
        delta = -delta

    steps = random.randint(3, 7)
    step_size = delta / steps

    for _ in range(steps):
        await page.mouse.wheel(0, step_size)
        await asyncio.sleep(random.uniform(0.04, 0.12))

    await pause(200, 500)
