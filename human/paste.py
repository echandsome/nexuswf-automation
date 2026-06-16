"""Human-like copy-and-paste into form fields."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from human.delays import micro_pause, pause, think
from human.mouse import click_locator

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page

MoveCallback = Callable[[float, float], None]


async def paste_into_locator(
    page: Page,
    locator: Locator,
    text: str,
    *,
    on_move: MoveCallback | None = None,
    pace: float = 1.0,
) -> None:
    """Click a field, paste from the clipboard, with natural mouse and pause timing."""
    scale = max(0.1, pace)

    await click_locator(page, locator, on_move=on_move)
    await think(280, 720, pace=scale)
    await pause(120, 320, pace=scale)

    await page.evaluate(
        """async (value) => {
            await navigator.clipboard.writeText(value);
        }""",
        text,
    )
    await micro_pause(pace=scale)
    await page.keyboard.press("Control+a")
    await micro_pause(pace=scale)
    await page.keyboard.press("Control+v")
    await pause(300, 650, pace=scale)
