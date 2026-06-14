"""Login page interactions for Nexus Workforce."""

from __future__ import annotations

import re

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from pages.base import BasePage


class LoginPage(BasePage):
    USERNAME_INPUT = "#username"
    PASSWORD_INPUT = "#password"
    SUBMIT_BUTTON = "button[type='submit']"

    @property
    def login_url(self) -> str:
        return f"{self.base_url}/login"

    async def open(self) -> None:
        """Navigate to the login page and wait for the form."""
        await self.page.goto(self.login_url, wait_until="domcontentloaded")
        await self.human.think(800, 1800)
        await self.page.locator(self.USERNAME_INPUT).wait_for(state="visible")

    async def fill_credentials(self, username: str, password: str) -> None:
        await self.human.type_text(self.USERNAME_INPUT, username)
        await self.human.pause(350, 900)
        await self.human.type_text(self.PASSWORD_INPUT, password)
        await self.human.pause(400, 1000)

    async def submit(self) -> None:
        await self.human.click(self.SUBMIT_BUTTON)

    async def login(self, username: str, password: str) -> None:
        """Complete the full login flow with human-like pacing."""
        await self.open()
        await self.fill_credentials(username, password)
        await self.submit()

    async def wait_for_post_login(self, timeout_ms: int = 30_000) -> str:
        """
        Wait until navigation away from the login page completes.
        Returns the final URL.
        """
        login_pattern = re.compile(r"/login/?(\?|$)")

        try:
            await self.page.wait_for_url(
                lambda url: not login_pattern.search(url),
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Login did not redirect away from the login page within the timeout. "
                "Check credentials or look for an error message on the page."
            ) from exc

        await self.human.think(600, 1400)
        return self.page.url
