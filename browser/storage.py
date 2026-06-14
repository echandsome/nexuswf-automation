"""Persist and restore browser cookies and local storage."""

from __future__ import annotations

from pathlib import Path

from playwright.async_api import BrowserContext


async def save_storage_state(context: BrowserContext, path: Path) -> None:
    """Write cookies and localStorage to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=str(path))


def storage_state_for_context(path: Path) -> dict | None:
    """Return Playwright storage_state kwargs if a saved session exists."""
    if path.is_file():
        return {"storage_state": str(path)}
    return None
