"""Authentication flow with saved-session reuse."""

from __future__ import annotations

import logging
import re

from browser.session import BrowserSession
from config.settings import Settings
from pages.login import LoginPage

logger = logging.getLogger(__name__)

DASHBOARD_PATH = "/employee-dashboard"
_LOGIN_PATTERN = re.compile(r"/login/?(\?|$)")
_DASHBOARD_PATTERN = re.compile(r"/employee-dashboard")


def is_login_url(url: str) -> bool:
    return bool(_LOGIN_PATTERN.search(url))


def is_dashboard_url(url: str) -> bool:
    return bool(_DASHBOARD_PATTERN.search(url))


async def ensure_logged_in(session: BrowserSession, settings: Settings) -> str:
    """
    Open the employee dashboard using saved browser state when available.
    Log in only if the site redirects to the login page.
    """
    dashboard_url = f"{settings.base_url}{DASHBOARD_PATH}"

    logger.info("Checking session at %s", dashboard_url)
    await session.page.goto(dashboard_url, wait_until="domcontentloaded")
    await session.human.think(600, 1200)

    if is_login_url(session.page.url):
        logger.info("Session expired or missing — logging in")
        login_page = LoginPage(session.page, session.human, settings.base_url)
        await login_page.login(settings.username, settings.password)
        final_url = await login_page.wait_for_dashboard()
        logger.info("Login succeeded — landed on %s", final_url)
        return final_url

    if not is_dashboard_url(session.page.url):
        raise RuntimeError(
            f"Expected employee dashboard or login page, got: {session.page.url}"
        )

    logger.info("Already authenticated — reusing saved session")
    return session.page.url
