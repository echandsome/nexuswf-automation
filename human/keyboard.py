"""Human-like keyboard input with variable per-character timing."""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import TYPE_CHECKING

from human.delays import micro_pause, pause, think
from human.mouse import click_locator

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page

MoveCallback = Callable[[float, float], None]


def _char_delay_ms(char: str, prev_char: str | None) -> float:
    base = random.uniform(55, 145)

    if char in " @._-":
        base += random.uniform(30, 90)
    elif char.isupper():
        base += random.uniform(20, 60)
    elif char.isdigit():
        base += random.uniform(10, 40)

    if prev_char and prev_char == char:
        base *= random.uniform(0.7, 0.9)

    return base


async def type_into_locator(
    page: Page,
    locator: Locator,
    text: str,
    *,
    on_move: MoveCallback | None = None,
    pace: float = 1.0,
) -> None:
    """Focus a field and type text character-by-character with natural variation."""
    scale = max(0.1, pace)
    await click_locator(page, locator, on_move=on_move)
    await pause(150, 400, pace=scale)

    await locator.fill("")
    await micro_pause(pace=scale)

    prev: str | None = None
    for char in text:
        if random.random() < 0.04:
            await think(180, 450, pace=scale)

        delay = _char_delay_ms(char, prev) * scale
        await page.keyboard.type(char, delay=delay)
        prev = char

        if random.random() < 0.08:
            await micro_pause(pace=scale)

    await pause(200, 500, pace=scale)
