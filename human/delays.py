"""Randomized pause utilities for human-like pacing."""

from __future__ import annotations

import asyncio
import random


async def pause(min_ms: float = 200, max_ms: float = 600, *, pace: float = 1.0) -> None:
    """Sleep for a random duration within the given millisecond range."""
    scale = max(0.1, pace)
    await asyncio.sleep(random.uniform(min_ms * scale, max_ms * scale) / 1000)


async def think(min_ms: float = 400, max_ms: float = 1200, *, pace: float = 1.0) -> None:
    """Longer pause simulating reading or decision-making."""
    await pause(min_ms, max_ms, pace=pace)


async def micro_pause(*, pace: float = 1.0) -> None:
    """Very short pause between rapid actions."""
    await pause(40, 120, pace=pace)
