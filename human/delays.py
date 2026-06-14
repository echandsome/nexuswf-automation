"""Randomized pause utilities for human-like pacing."""

from __future__ import annotations

import asyncio
import random


async def pause(min_ms: float = 200, max_ms: float = 600) -> None:
    """Sleep for a random duration within the given millisecond range."""
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)


async def think(min_ms: float = 400, max_ms: float = 1200) -> None:
    """Longer pause simulating reading or decision-making."""
    await pause(min_ms, max_ms)


async def micro_pause() -> None:
    """Very short pause between rapid actions."""
    await pause(40, 120)
