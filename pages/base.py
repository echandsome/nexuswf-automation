"""Base page object with shared navigation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from human.actor import HumanActor

if TYPE_CHECKING:
    from playwright.async_api import Page


class BasePage:
    def __init__(self, page: Page, human: HumanActor, base_url: str) -> None:
        self.page = page
        self.human = human
        self.base_url = base_url.rstrip("/")

    @property
    def url(self) -> str:
        return self.page.url
