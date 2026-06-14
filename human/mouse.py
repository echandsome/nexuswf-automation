"""Bezier-curve mouse movement and natural click targeting."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from typing import TYPE_CHECKING

from human.delays import micro_pause, pause

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page

MoveCallback = Callable[[float, float], None]


def _cubic_bezier(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
    u = 1 - t
    return u**3 * p0 + 3 * u**2 * t * p1 + 3 * u * t**2 * p2 + t**3 * p3


def _random_control_points(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    mid_x = (start_x + end_x) / 2
    mid_y = (start_y + end_y) / 2
    spread_x = max(abs(end_x - start_x) * random.uniform(0.15, 0.45), 20)
    spread_y = max(abs(end_y - start_y) * random.uniform(0.15, 0.45), 15)

    cp1 = (
        mid_x + random.uniform(-spread_x, spread_x),
        mid_y + random.uniform(-spread_y, spread_y),
    )
    cp2 = (
        mid_x + random.uniform(-spread_x, spread_x),
        mid_y + random.uniform(-spread_y, spread_y),
    )
    return cp1, cp2


async def move_to(
    page: Page,
    x: float,
    y: float,
    *,
    start: tuple[float, float] | None = None,
) -> None:
    """Move the mouse along a cubic Bezier curve to (x, y)."""
    start_x, start_y = start or (random.randint(200, 600), random.randint(200, 400))
    cp1, cp2 = _random_control_points(start_x, start_y, x, y)
    step_count = random.randint(18, 35)

    for i in range(1, step_count + 1):
        t = i / step_count
        bx = _cubic_bezier(t, start_x, cp1[0], cp2[0], x)
        by = _cubic_bezier(t, start_y, cp1[1], cp2[1], y)
        await page.mouse.move(bx, by)
        await asyncio.sleep(random.uniform(0.004, 0.018))


def _target_point_in_box(box: dict[str, float]) -> tuple[float, float]:
    margin_x = box["width"] * random.uniform(0.2, 0.35)
    margin_y = box["height"] * random.uniform(0.25, 0.4)
    x = box["x"] + margin_x + random.uniform(0, max(box["width"] - 2 * margin_x, 1))
    y = box["y"] + margin_y + random.uniform(0, max(box["height"] - 2 * margin_y, 1))
    return x, y


async def click_locator(
    page: Page,
    locator: Locator,
    *,
    on_move: MoveCallback | None = None,
) -> None:
    """Scroll element into view, move naturally, and click."""
    await locator.scroll_into_view_if_needed()
    await pause(80, 220)

    box = await locator.bounding_box()
    if box is None:
        await locator.click()
        return

    x, y = _target_point_in_box(box)
    await move_to(page, x, y)
    if on_move:
        on_move(x, y)

    await micro_pause()
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.045, 0.12))
    await page.mouse.up()
    await pause(120, 350)
