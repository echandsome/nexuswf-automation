"""Unified facade for human-like browser interactions."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from human.delays import pause, think
from human.keyboard import type_into_locator
from human.mouse import click_locator, move_to
from human.paste import paste_into_locator
from human.scroll import scroll_page

if TYPE_CHECKING:
    from playwright.async_api import Page


class HumanActor:
    """Orchestrates natural mouse, keyboard, scroll, and timing behavior."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self._mouse_x = random.randint(300, 700)
        self._mouse_y = random.randint(200, 450)
        self._pace = 1.0

    def set_pace(self, factor: float) -> None:
        self._pace = max(0.1, factor)

    def reset_pace(self) -> None:
        self._pace = 1.0

    async def pause(self, min_ms: float = 200, max_ms: float = 600) -> None:
        await pause(min_ms, max_ms, pace=self._pace)

    async def think(self, min_ms: float = 400, max_ms: float = 1200) -> None:
        await think(min_ms, max_ms, pace=self._pace)

    async def move_to(self, x: float, y: float) -> None:
        await move_to(self.page, x, y, start=(self._mouse_x, self._mouse_y))
        self._mouse_x = x
        self._mouse_y = y

    async def click(self, selector: str) -> None:
        locator = self.page.locator(selector)
        await click_locator(
            self.page,
            locator,
            on_move=lambda x, y: self._update_mouse(x, y),
        )

    async def type_text(self, selector: str, text: str) -> None:
        locator = self.page.locator(selector)
        await type_into_locator(
            self.page,
            locator,
            text,
            on_move=lambda x, y: self._update_mouse(x, y),
            pace=self._pace,
        )

    async def paste_text(self, selector: str, text: str) -> None:
        """Paste text into a field after moving the mouse to click it."""
        locator = self.page.locator(selector)
        await paste_into_locator(
            self.page,
            locator,
            text,
            on_move=lambda x, y: self._update_mouse(x, y),
            pace=self._pace,
        )

    async def scroll(self, *, direction: str = "down", amount: int | None = None) -> None:
        await scroll_page(self.page, direction=direction, amount=amount)

    async def select_option(self, selector: str, value: str) -> None:
        """Open a select and choose an option with natural pacing."""
        locator = self.page.locator(selector)
        await click_locator(
            self.page,
            locator,
            on_move=lambda x, y: self._update_mouse(x, y),
        )
        await think(350, 900, pace=self._pace)
        await locator.select_option(value=value)
        await pause(200, 500, pace=self._pace)

    def _update_mouse(self, x: float, y: float) -> None:
        self._mouse_x = x
        self._mouse_y = y
